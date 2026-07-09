#!/usr/bin/env python3
"""
h5-port-verify.py

H5 포팅 검증 스크립트.
C# 전처리문 구조를 파싱해 플랫폼별 처리 누락을 감지한다.

결과 3종류:
  ❌ 미처리    — 가드 없이 메서드 호출 (실제 이슈)
  ⚠️ 확인 필요 — #elif UNITY_WEBGL 블록 안 호출 (사람 판단 필요)
  ✅ 이상 없음

사용법:
  python h5-port-verify.py --platform WEBGL_PUREWEB --scripts Assets/Script
  python h5-port-verify.py --platform WEBGL_TOSS    --scripts Assets/Script
  python h5-port-verify.py --platform WEBGL_PUREWEB --method ShowRewardAD --method Purchase
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


# ── 전처리문 파싱 정규식 ─────────────────────────────────────────────────────────
# C#은 # 다음 공백 허용: "# endif", "#  if" 등 모두 유효
_RE_PREPROC = re.compile(r'^#\s*(if|elif|else|endif)\b(.*)?$')


def parse_preproc(line: str):
    """전처리 지시문 줄 파싱. 반환: (directive, condition) 또는 None"""
    m = _RE_PREPROC.match(line)
    if m:
        return m.group(1), (m.group(2) or '').strip()
    return None


# ── 공통 유틸리티 ────────────────────────────────────────────────────────────────

_DEFINITION_PATTERN = re.compile(
    r'\b(public|private|protected|internal|static|virtual|override|abstract|async)\b'
)


def is_definition_line(code: str) -> bool:
    """메서드/함수 정의 줄이면 True."""
    return bool(_DEFINITION_PATTERN.search(code))


def build_pattern(method_names: list) -> re.Pattern:
    """단어 경계 + '(' 로 변수명 오탐을 방지하는 메서드 호출 패턴."""
    escaped = [re.escape(m) for m in method_names]
    return re.compile(r'\b(?:' + '|'.join(escaped) + r')\s*\(')


# ── 전처리 조건 불리언 평가 (check-editor-shadow 모드) ──────────────────────────

_RE_COND_COMMENT = re.compile(r'//.*$|/\*.*?\*/')
_RE_COND_SYMBOL = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
_RE_COND_NOT = re.compile(r'!(?!=)')


def strip_condition_comment(cond: str) -> str:
    """조건 문자열 끝의 // 주석과 /* */ 주석을 제거한다."""
    return _RE_COND_COMMENT.sub(' ', cond).strip()


def condition_symbols(cond: str) -> set:
    """조건 문자열에 등장하는 심볼 집합 (true/false 리터럴 제외)."""
    return set(_RE_COND_SYMBOL.findall(strip_condition_comment(cond))) - {'true', 'false'}


def eval_condition(cond: str, defines: set):
    """
    전처리 조건을 define 집합으로 평가한다. 반환: True/False, 파싱 불가 시 None.
    지원: 심볼, ! && || 괄호, true/false 리터럴, == != 비교, 주석.
    """
    expr = strip_condition_comment(cond)

    def symbol_to_bool(match):
        symbol = match.group(0)
        if symbol == 'true':
            return 'True'
        if symbol == 'false':
            return 'False'
        return 'True' if symbol in defines else 'False'

    expr = _RE_COND_SYMBOL.sub(symbol_to_bool, expr)
    expr = expr.replace('&&', ' and ').replace('||', ' or ')
    expr = _RE_COND_NOT.sub(' not ', expr)
    try:
        return bool(eval(expr, {'__builtins__': {}}, {}))
    except Exception:
        return None


# ── 데이터 클래스 ────────────────────────────────────────────────────────────────

@dataclass
class Frame:
    cond_type: str
    directive_line: int
    in_else: bool = False


@dataclass
class ScanResult:
    definite: list = field(default_factory=list)   # [(rel, lineno, method)]
    ambiguous: list = field(default_factory=list)  # [(rel, lineno, method, directive_line)]
    filtered: int = 0
    def_filtered: int = 0


@dataclass
class VoidHit:
    rel: str
    lineno: int
    severity: str   # CONTROL_FLOW | STATE_UNDEF | BEHAVIOR_GAP
    cond: str


@dataclass
class CallerHit:
    rel: str
    lineno: int
    caller_var: str    # 호출에 사용된 변수명 또는 클래스명
    wrapper_class: str # 래퍼 클래스명
    method: str        # 호출된 메서드명


@dataclass
class ChainArm:
    directive: str  # if | elif | else
    cond: str
    lineno: int
    value: bool     # 에디터+WebGL defines 기준 평가값 (else는 True, 평가 실패는 False)


@dataclass
class ShadowHit:
    rel: str
    taken_line: int
    taken_cond: str     # 에디터에서 실제로 타는 WEBGL 분기
    shadowed_line: int
    shadowed_cond: str  # 가로채인 원본 UNITY_EDITOR 분기


# ── 조건 분류기 ──────────────────────────────────────────────────────────────────

class ConditionClassifier:
    """
    #if / #elif 조건 문자열을 분류한다.
    플랫폼 심볼 집합을 생성자에서 주입받아 새 플랫폼 추가 시 내부 수정이 필요 없다.

    분류 결과:
      PLATFORM      — 검증 대상 플랫폼 블록
      TOSS          — 상대 플랫폼 블록
      NOT_WEBGL     — !UNITY_WEBGL
      OTHER_NATIVE  — UNITY_IOS / UNITY_ANDROID / UNITY_STANDALONE / UNITY_EDITOR
      WEBGL_GENERIC — UNITY_WEBGL 단독 (#if 첫 분기)
      NEUTRAL       — 그 외
    """
    _NATIVE_PAT = re.compile(r'UNITY_IOS|UNITY_ANDROID|UNITY_STANDALONE|UNITY_EDITOR')
    _ALL_WEBGL = {"WEBGL_TOSS", "WEBGL_PUREWEB", "WEBGL_DEV_VER", "WEBGL_LIVE_VER"}

    def __init__(self, platform: str, webgl_generic_safe: bool = True):
        self._platform = platform
        self._other_webgl = self._ALL_WEBGL - {platform}
        self.webgl_generic_safe = webgl_generic_safe

    def classify(self, condition: str, frames: list) -> str:
        cond = condition.strip()

        # UNITY_WEBGL && PLATFORM 한 줄 결합
        if "UNITY_WEBGL" in cond and self._platform in cond:
            return "PLATFORM"

        # UNITY_WEBGL + 다른 WebGL 심볼
        if "UNITY_WEBGL" in cond and any(p in cond for p in self._other_webgl):
            return "TOSS"

        # PLATFORM 심볼만 (중첩 패턴: #if UNITY_WEBGL 안에 #if WEBGL_PUREWEB)
        if self._platform in cond and "UNITY_WEBGL" not in cond:
            for frame in frames:
                if frame.cond_type in ("WEBGL_GENERIC", "PLATFORM") and not frame.in_else:
                    return "PLATFORM"
            return "NEUTRAL"

        # 다른 WebGL 심볼만 (중첩 패턴: #if UNITY_WEBGL 안에 #elif WEBGL_TOSS)
        if any(p in cond for p in self._other_webgl) and "UNITY_WEBGL" not in cond:
            for frame in frames:
                if frame.cond_type in ("WEBGL_GENERIC", "PLATFORM", "TOSS") and not frame.in_else:
                    return "TOSS"

        if re.search(r'!\s*UNITY_WEBGL', cond):
            return "NOT_WEBGL"

        if self._NATIVE_PAT.search(cond):
            return "OTHER_NATIVE"

        if "UNITY_WEBGL" in cond:
            return "WEBGL_GENERIC"

        return "NEUTRAL"


# ── 전처리문 스택 ────────────────────────────────────────────────────────────────

class PreprocStack:
    """전처리문 #if/#elif/#else/#endif 중첩 상태를 관리한다."""

    def __init__(self, classifier: ConditionClassifier):
        self.frames: list[Frame] = []
        self._classifier = classifier

    def update(self, directive: str, cond: str, lineno: int = 0):
        """전처리문 지시문 하나를 스택에 반영한다."""
        if directive == 'if':
            self._push(cond, lineno)
        elif directive == 'elif':
            self._to_elif(cond, lineno)
        elif directive == 'else':
            self._to_else()
        elif directive == 'endif':
            self._pop()

    def _push(self, condition: str, lineno: int):
        ctype = self._classifier.classify(condition, self.frames)
        self.frames.append(Frame(ctype, lineno))

    def _to_elif(self, condition: str, lineno: int):
        if not self.frames:
            return
        prev_type = self.frames[-1].cond_type
        new_type = self._classifier.classify(condition, self.frames)
        # #elif UNITY_WEBGL 이 TOSS 다음 → 암묵적 PLATFORM 분기
        if new_type == "WEBGL_GENERIC" and prev_type == "TOSS":
            new_type = "PLATFORM"
        # #elif UNITY_WEBGL 이 TOSS 다음이 아님 → 사람 판단 필요
        elif new_type == "WEBGL_GENERIC":
            new_type = "AMBIGUOUS"
        self.frames[-1].cond_type = new_type
        self.frames[-1].in_else = False
        self.frames[-1].directive_line = lineno

    def _to_else(self):
        if self.frames:
            self.frames[-1].in_else = True

    def _pop(self):
        if self.frames:
            self.frames.pop()

    def status(self) -> str:
        """현재 위치 판정: SAFE / AMBIGUOUS / UNSAFE"""
        safe_types = {"NOT_WEBGL", "OTHER_NATIVE", "TOSS"}
        if self._classifier.webgl_generic_safe:
            safe_types.add("WEBGL_GENERIC")
        for frame in self.frames:
            if frame.cond_type == "PLATFORM":
                return "SAFE"
            if frame.cond_type in safe_types and not frame.in_else:
                return "SAFE"
        for frame in self.frames:
            if frame.cond_type == "AMBIGUOUS" and not frame.in_else:
                return "AMBIGUOUS"
        return "UNSAFE"

    def is_accessible(self) -> bool:
        """대상 플랫폼 빌드에서 실행되는 위치인지."""
        for frame in self.frames:
            if frame.cond_type in ("TOSS", "NOT_WEBGL", "OTHER_NATIVE") and not frame.in_else:
                return False
        return True

    def ambiguous_frame(self):
        for frame in self.frames:
            if frame.cond_type == "AMBIGUOUS" and not frame.in_else:
                return frame
        return None


# ── C# 파일 파서 ─────────────────────────────────────────────────────────────────

class PreprocParser:
    """
    C# 파일을 한 줄씩 읽어 전처리문 스택을 갱신하고,
    코드 줄만 (lineno, code, stack) 으로 yield한다.

    블록 주석·전처리문 처리를 캡슐화해 스캐너가 파싱 세부사항을 알 필요 없게 한다.
    """

    def __init__(self, classifier: ConditionClassifier):
        self._classifier = classifier

    def parse(self, path: Path) -> Generator:
        stack = PreprocStack(self._classifier)
        in_block_comment = False
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except Exception:
            return
        for lineno, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if in_block_comment:
                if "*/" in line:
                    in_block_comment = False
                continue
            if "/*" in line:
                before = line[:line.index("/*")]
                if "*/" not in line[line.index("/*"):]:
                    in_block_comment = True
                    line = before
            pp = parse_preproc(line)
            if pp:
                stack.update(*pp, lineno)
                continue
            yield lineno, line.split("//")[0], stack


# ── Pass 1: 정의 스캐너 ─────────────────────────────────────────────────────────

class DefinitionScanner:
    """
    Pass 1: 대상 플랫폼에서 접근 가능한 메서드 정의 집합을 반환한다.
    이 집합은 CallScanner에서 가드 없는 호출이 실제 이슈인지 판단하는 데 쓰인다.
    """

    def __init__(self, parser: PreprocParser, pattern: re.Pattern):
        self._parser = parser
        self._pattern = pattern

    def _scan_file(self, path: Path) -> set:
        found = set()
        for _lineno, code, stack in self._parser.parse(path):
            if not is_definition_line(code):
                continue
            m = self._pattern.search(code)
            if m and stack.is_accessible():
                found.add(m.group(0).rstrip("( \t"))
        return found

    def scan(self, files: list) -> set:
        safe_methods: set = set()
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._scan_file, f) for f in files]
            for future in as_completed(futures):
                safe_methods |= future.result()
        return safe_methods


# ── Pass 2: 호출 스캐너 ─────────────────────────────────────────────────────────

class CallScanner:
    """
    Pass 2: 가드 없이 호출되는 메서드를 탐지한다.
    DefinitionScanner의 safe_methods와 예외 로그를 참조해 false positive를 제거한다.
    """

    def __init__(self, parser: PreprocParser, pattern: re.Pattern,
                 safe_methods: set, safe_exceptions: set):
        self._parser = parser
        self._pattern = pattern
        self._safe_methods = safe_methods
        self._safe_exceptions = safe_exceptions

    def _scan_file(self, path: Path, rel_str: str) -> tuple:
        definite, ambiguous = [], []
        filtered = def_filtered = 0
        for lineno, code, stack in self._parser.parse(path):
            if is_definition_line(code):
                continue
            m = self._pattern.search(code)
            if not m:
                continue
            matched = m.group(0).rstrip("( \t")
            s = stack.status()
            if s == "SAFE":
                continue
            if s == "AMBIGUOUS":
                af = stack.ambiguous_frame()
                dl = af.directive_line if af else 0
                if (rel_str, dl) in self._safe_exceptions:
                    filtered += 1
                else:
                    ambiguous.append((lineno, matched, dl))
            else:  # UNSAFE
                if matched in self._safe_methods:
                    def_filtered += 1
                else:
                    definite.append((lineno, matched))
        return definite, ambiguous, filtered, def_filtered

    def scan(self, files: list, base: Path) -> ScanResult:
        result = ScanResult()
        with ThreadPoolExecutor() as executor:
            future_to_rel = {
                executor.submit(self._scan_file, f, str(f.relative_to(base))): str(f.relative_to(base))
                for f in files
            }
            for future in as_completed(future_to_rel):
                rel = future_to_rel[future]
                d, a, f, df = future.result()
                for lineno, method in d:
                    result.definite.append((rel, lineno, method))
                for lineno, method, dl in a:
                    result.ambiguous.append((rel, lineno, method, dl))
                result.filtered += f
                result.def_filtered += df
        result.definite.sort()
        result.ambiguous.sort()
        return result


# ── WebGL 공백(Void) 스캐너 ──────────────────────────────────────────────────────

_VOID_YIELD_RE = re.compile(r'\byield\b')
_VOID_STATE_RE = re.compile(r'\.SetActive\s*\(|\.enabled\s*=')
_VOID_LOOP_RE  = re.compile(r'\bIEnumerator\b')


def _void_severity(body_lines: list, context_lines: list) -> str:
    body    = '\n'.join(body_lines)
    context = '\n'.join(context_lines)
    if _VOID_YIELD_RE.search(body) or _VOID_LOOP_RE.search(context):
        return 'CONTROL_FLOW'
    if _VOID_STATE_RE.search(body):
        return 'STATE_UNDEF'
    return 'BEHAVIOR_GAP'


class VoidScanner:
    """
    WebGL 공백 체인 탐지기.
    OTHER_NATIVE arm은 있지만 WEBGL arm도 #else도 없는 #if...#endif 블록을 탐지한다.
    PreprocParser와 독립적으로 동작하므로 기존 verify 흐름에 영향 없음.
    """

    def __init__(self, classifier: ConditionClassifier):
        self._classifier = classifier

    def scan_file(self, path: Path, base: Path) -> list:
        try:
            raw_lines = path.read_text(encoding='utf-8-sig').splitlines()
        except Exception:
            return []

        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = str(path)
        results = []

        # stack entry: [cond_type, start_line, has_native_arm, has_webgl_arm, in_else, body_lines, cond_str]
        stack: list = []
        in_block_comment = False

        for lineno, raw in enumerate(raw_lines, 1):
            line = raw.strip()

            if in_block_comment:
                if '*/' in line:
                    in_block_comment = False
                continue
            if '/*' in line:
                before = line[:line.index('/*')]
                if '*/' not in line[line.index('/*'):]:
                    in_block_comment = True
                line = before

            pp = parse_preproc(line)
            if not pp:
                code = line.split('//')[0].strip()
                if code and stack:
                    stack[-1][5].append(code)
                continue

            directive, cond = pp

            if directive == 'if':
                pseudo = [Frame(s[0], s[1]) for s in stack]
                ctype = self._classifier.classify(cond, pseudo)
                stack.append([
                    ctype, lineno,
                    ctype == 'OTHER_NATIVE',
                    ctype in ('PLATFORM', 'WEBGL_GENERIC', 'AMBIGUOUS'),
                    False, [], cond,
                ])

            elif directive == 'elif' and stack:
                entry = stack[-1]
                pseudo = [Frame(s[0], s[1]) for s in stack[:-1]]
                new_type = self._classifier.classify(cond, pseudo)
                if new_type == 'WEBGL_GENERIC' and entry[0] == 'TOSS':
                    new_type = 'PLATFORM'
                elif new_type == 'WEBGL_GENERIC':
                    new_type = 'AMBIGUOUS'
                entry[0] = new_type
                if new_type == 'OTHER_NATIVE':
                    entry[2] = True
                if new_type in ('PLATFORM', 'WEBGL_GENERIC', 'AMBIGUOUS'):
                    entry[3] = True

            elif directive == 'else' and stack:
                stack[-1][4] = True

            elif directive == 'endif' and stack:
                ctype, start_line, has_native, has_webgl, in_else, body, cond_str = stack.pop()
                if has_native and not has_webgl and not in_else:
                    ctx = raw_lines[max(0, start_line - 6):start_line - 1]
                    sev = _void_severity(body, ctx)
                    results.append(VoidHit(rel, start_line, sev, cond_str))

        return results

    def scan(self, files: list, base: Path) -> list:
        results = []
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.scan_file, f, base) for f in files]
            for future in as_completed(futures):
                results.extend(future.result())
        results.sort(key=lambda h: (h.rel, h.lineno))
        return results


# ── 호출부 역추적 스캐너 ──────────────────────────────────────────────────────

_LIFECYCLE_METHODS = {
    'Start', 'Awake', 'Update', 'FixedUpdate', 'LateUpdate',
    'OnDestroy', 'OnEnable', 'OnDisable', 'OnApplicationPause',
    'OnApplicationFocus', 'OnTriggerEnter', 'OnCollisionEnter',
    'OnTriggerExit', 'OnCollisionExit', 'OnDrawGizmos',
}


class CallerScanner:
    """
    래퍼 클래스의 public 메서드를 호출하는 파일을 역추적한다.
    tree-sitter로 타입을 추적하고, PreprocParser로 WEBGL 가드를 확인한다.

    지원하는 타입 추론:
      - 명시적 타입 선언: ServiceManager _svc;
      - new 표현식:       var x = new ServiceManager();
      - 제네릭 메서드:    var x = GetComponent<ServiceManager>();
      - 메서드 파라미터:  void Foo(ServiceManager svc)

    추론 불가 케이스 (허용된 한계):
      - var x = GetServiceManager();  (불투명 반환형)
      - 리플렉션·델리게이트 기반 간접 호출
    """

    def __init__(self, classifier: ConditionClassifier):
        self._classifier = classifier
        self._wrappers: dict = {}  # {ClassName: {method1, method2, ...}}
        try:
            from tree_sitter_languages import get_parser as _ts_get
            self._ts_parser = _ts_get('c_sharp')
        except ImportError:
            self._ts_parser = None

    def _get_safe_lines(self, path: Path) -> set:
        """PreprocParser로 WEBGL-safe 줄 번호 집합을 반환한다."""
        safe: set = set()
        parser = PreprocParser(self._classifier)
        for lineno, _code, stack in parser.parse(path):
            if stack.status() == 'SAFE':
                safe.add(lineno)
        return safe

    def _extract_wrapper_info(self, wrapper_file: Path) -> tuple:
        """래퍼 파일에서 (클래스명, public 메서드 집합)을 추출한다."""
        if self._ts_parser is None:
            return ('', set())
        try:
            source = wrapper_file.read_bytes()
        except Exception:
            return ('', set())

        tree = self._ts_parser.parse(source)

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        class_name = ''
        methods: set = set()

        def walk(node):
            nonlocal class_name
            if node.type == 'class_declaration':
                for child in node.children:
                    if child.type == 'identifier' and not class_name:
                        class_name = get_text(child)
                for child in node.children:
                    walk(child)
            elif node.type == 'method_declaration':
                is_public = any(
                    get_text(c) == 'public'
                    for c in node.children if c.type == 'modifier'
                )
                if is_public:
                    for child in node.children:
                        if child.type == 'identifier':
                            m = get_text(child)
                            if m not in _LIFECYCLE_METHODS:
                                methods.add(m)
            else:
                for child in node.children:
                    walk(child)

        walk(tree.root_node)
        return (class_name, methods)

    def load_wrappers(self, wrapper_files: list):
        """래퍼 파일들에서 클래스명·메서드 목록을 추출해 내부 dict에 저장한다."""
        for wf in wrapper_files:
            class_name, methods = self._extract_wrapper_info(wf)
            if class_name and methods:
                self._wrappers[class_name] = methods

    def _extract_type_map(self, tree_node, source: bytes) -> dict:
        """AST에서 {변수명: 클래스명} 매핑을 추출한다."""
        type_map: dict = {}
        wrapper_names = set(self._wrappers.keys())

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        def infer_from_rhs(rhs) -> str:
            if rhs.type == 'object_creation_expression':
                for c in rhs.children:
                    if c.type == 'identifier' and get_text(c) in wrapper_names:
                        return get_text(c)
            elif rhs.type == 'invocation_expression' and rhs.children:
                fn = rhs.children[0]
                if fn.type == 'generic_name':
                    for c in fn.children:
                        if c.type == 'type_argument_list':
                            for arg in c.children:
                                if arg.type == 'identifier' and get_text(arg) in wrapper_names:
                                    return get_text(arg)
            return ''

        def process_var_decl(vd):
            if not vd.children:
                return
            type_node = vd.children[0]
            if type_node.type == 'identifier':
                tname = get_text(type_node)
                if tname in wrapper_names:
                    for c in vd.children[1:]:
                        if c.type == 'variable_declarator' and c.children:
                            vname = get_text(c.children[0])
                            if vname:
                                type_map[vname] = tname
            elif type_node.type == 'implicit_type':
                for c in vd.children[1:]:
                    if c.type == 'variable_declarator' and c.children:
                        vname = get_text(c.children[0])
                        for sub in c.children:
                            if sub.type == 'equals_value_clause' and sub.children:
                                inferred = infer_from_rhs(sub.children[-1])
                                if inferred and vname:
                                    type_map[vname] = inferred

        def walk(node):
            if node.type in ('field_declaration', 'local_declaration_statement'):
                for c in node.children:
                    if c.type == 'variable_declaration':
                        process_var_decl(c)
            elif node.type == 'parameter':
                ch = node.children
                if len(ch) >= 2 and ch[0].type == 'identifier':
                    tname = get_text(ch[0])
                    if tname in wrapper_names:
                        vname = get_text(ch[-1])
                        if vname:
                            type_map[vname] = tname
            for c in node.children:
                walk(c)

        walk(tree_node)
        return type_map

    def _extract_calls(self, tree_node, source: bytes) -> list:
        """
        AST에서 [(lineno, root_identifier, method_name)] 호출 목록을 추출한다.

        체인 호출 지원: ServiceManager.Instance.ShowVideo()
          → root_identifier = ServiceManager, method_name = ShowVideo
        단일 호출 지원: _svc.ShowVideo()
          → root_identifier = _svc, method_name = ShowVideo
        """
        calls = []

        def get_text(node):
            return source[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

        def root_identifier(node):
            """member_access_expression에서 가장 왼쪽 identifier를 반환한다."""
            cur = node
            while cur.type == 'member_access_expression' and cur.children:
                cur = cur.children[0]
            if cur.type == 'identifier':
                return cur
            return None

        def walk(node):
            if node.type == 'invocation_expression' and node.children:
                mae = node.children[0]
                if mae.type == 'member_access_expression' and len(mae.children) >= 3:
                    mth_n = mae.children[2]
                    root_n = root_identifier(mae.children[0])
                    if root_n is not None and mth_n.type == 'identifier':
                        calls.append((
                            mth_n.start_point[0] + 1,
                            get_text(root_n),
                            get_text(mth_n),
                        ))
            for c in node.children:
                walk(c)

        walk(tree_node)
        return calls

    def scan_file(self, path: Path, base: Path, wrapper_rels: set) -> list:
        if self._ts_parser is None:
            return []
        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = str(path)
        if rel in wrapper_rels:
            return []
        try:
            source = path.read_bytes()
        except Exception:
            return []

        safe_lines = self._get_safe_lines(path)
        tree = self._ts_parser.parse(source)
        type_map = self._extract_type_map(tree.root_node, source)
        calls = self._extract_calls(tree.root_node, source)

        results = []
        for lineno, obj_name, method_name in calls:
            if lineno in safe_lines:
                continue
            if obj_name in self._wrappers:
                resolved = obj_name
            elif obj_name in type_map:
                resolved = type_map[obj_name]
            else:
                continue
            if method_name not in self._wrappers.get(resolved, set()):
                continue
            results.append(CallerHit(rel, lineno, obj_name, resolved, method_name))

        return results

    def scan(self, scan_files: list, base: Path, wrapper_rels: set) -> list:
        results = []
        with ThreadPoolExecutor() as exe:
            futs = [exe.submit(self.scan_file, f, base, wrapper_rels) for f in scan_files]
            for fut in as_completed(futs):
                results.extend(fut.result())
        results.sort(key=lambda h: (h.rel, h.lineno))
        return results


# ── 예외 로그 ──────────────────────────────────────────────────────────────────

def load_exceptions(log_path: Path) -> set:
    if not log_path.exists():
        return set()
    try:
        entries = json.loads(log_path.read_text(encoding="utf-8"))
        return {
            (e["file"], e["directive_line"])
            for e in entries
            if e.get("decision") == "safe"
        }
    except Exception:
        return set()


# ── PORTING_VOCAB.md 파싱 ──────────────────────────────────────────────────────

def extract_methods(method_col: str) -> list:
    """
    메서드/클래스명 컬럼에서 실제 메서드명 추출.
      `Class.Method()` → Method
      `Class.ShowVideo_Continue/BossMode/Gem()` → ShowVideo_Continue, ShowVideo_BossMode, ShowVideo_Gem
      상속 선언(`Class : Interface`)은 제외
    """
    results = []
    for token in re.findall(r'`([^`]+)`', method_col):
        if ':' in token:
            continue
        token = re.sub(r'\([^)]*\)', '', token).strip()
        base = token.split('.')[-1] if '.' in token else token
        if '/' in base:
            parts_list = base.split('/')
            if '_' in parts_list[0]:
                prefix = '_'.join(parts_list[0].split('_')[:-1]) + '_'
                results.append(parts_list[0])
                for part in parts_list[1:]:
                    results.append(prefix + part)
            else:
                results.extend(p for p in parts_list if p)
        elif base:
            results.append(base)
    return results


def parse_vocab(vocab_path: Path) -> dict:
    """
    PORTING_VOCAB.md (5컬럼: 시스템|메서드명|파일|플레이스홀더|비고) 파싱.
    반환: {플레이스홀더키: [메서드명, ...]}
    """
    vocab = {}
    if not vocab_path.exists():
        return vocab
    for line in vocab_path.read_text(encoding="utf-8-sig").splitlines():
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) < 4:
            continue
        placeholder = parts[3].strip("`{} ")
        if not placeholder or not re.match(r'^[A-Z][A-Z0-9_]+$', placeholder):
            continue
        methods = extract_methods(parts[1])
        if methods:
            vocab[placeholder] = methods
    return vocab


# ── 에디터 섀도잉 스캐너 (check-editor-shadow 모드) ──────────────────────────────

class EditorShadowScanner:
    """
    포팅으로 삽입된 WEBGL 분기가 에디터(WebGL 빌드타겟)에서
    원본 UNITY_EDITOR 분기를 가로채는 체인을 탐지한다.

    불변식: 포팅은 기존 define 조합이 타던 분기를 바꾸지 않는다.
    에디터+WebGL 타겟 조합에서 체인의 첫 참 분기가 WEBGL 계열 심볼 분기이고,
    그 아래에 UNITY_EDITOR를 언급하며 참으로 평가되는 분기가 있으면 섀도잉이다.
    수정도 기계적: 타는 분기 조건에 '&& !UNITY_EDITOR' 추가.
    """

    def __init__(self, platform: str):
        self.defines = {'UNITY_EDITOR', 'UNITY_WEBGL', platform, 'WEBGL_DEV_VER'}
        self.hits: list = []
        self.eval_failures: list = []  # [(rel, lineno, cond)]

    @staticmethod
    def _is_ported_arm(symbols: set) -> bool:
        return any(s == 'UNITY_WEBGL' or s.startswith('WEBGL_') for s in symbols)

    @staticmethod
    def _frame_active(frame: dict) -> bool:
        return frame['parent_active'] and frame['taken'] == len(frame['arms']) - 1

    def scan_file(self, path: Path, rel: str):
        try:
            raw_lines = path.read_text(encoding='utf-8-sig').splitlines()
        except Exception as read_error:
            print(f"⚠ 읽기 실패: {rel} ({read_error})")
            return

        # frame: {'arms': [ChainArm], 'taken': 첫 참 분기 인덱스|None, 'parent_active': bool}
        chain_stack: list = []
        in_block_comment = False

        for lineno, raw in enumerate(raw_lines, 1):
            line = raw.strip()

            if in_block_comment:
                if '*/' in line:
                    in_block_comment = False
                continue
            if line.startswith('/*') and '*/' not in line:
                in_block_comment = True
                continue

            parsed = parse_preproc(line)
            if not parsed:
                continue
            directive, cond = parsed

            if directive == 'if':
                parent_active = self._frame_active(chain_stack[-1]) if chain_stack else True
                chain_stack.append({'arms': [], 'taken': None, 'parent_active': parent_active})

            if directive in ('if', 'elif', 'else'):
                if not chain_stack:
                    continue
                frame = chain_stack[-1]
                if directive == 'else':
                    arm_value = True
                else:
                    arm_value = eval_condition(cond, self.defines)
                    if arm_value is None:
                        self.eval_failures.append((rel, lineno, cond.strip()))
                        arm_value = False
                frame['arms'].append(ChainArm(directive, cond.strip(), lineno, arm_value))
                if frame['taken'] is None and arm_value:
                    frame['taken'] = len(frame['arms']) - 1
            elif directive == 'endif':
                if not chain_stack:
                    continue
                self._judge_chain(chain_stack.pop(), rel)

    def _judge_chain(self, frame: dict, rel: str):
        """체인 종료 시 판정. 컴파일되지 않는 중첩 체인(parent 비활성)은 제외."""
        if not frame['parent_active'] or frame['taken'] is None:
            return
        arms = frame['arms']
        taken_arm = arms[frame['taken']]
        if not self._is_ported_arm(condition_symbols(taken_arm.cond)):
            return
        for shadowed_arm in arms[frame['taken'] + 1:]:
            if 'UNITY_EDITOR' in condition_symbols(shadowed_arm.cond) and shadowed_arm.value:
                self.hits.append(ShadowHit(rel, taken_arm.lineno, taken_arm.cond,
                                           shadowed_arm.lineno, shadowed_arm.cond))
                return


# ── 메인 ──────────────────────────────────────────────────────────────────────

VOCAB_KEYS = ["AD_REWARDED_METHOD", "IAP_METHOD", "SAVE_METHOD"]

TOSS_HANDLER_METHODS = [
    "InitializeAppsInTossBannerAd",
    "AttachAppsInTossBannerAd",
    "DetachAppsInTossBannerAd",
    "ClaimPromotionRewardForGameForManaged",
    "ClaimPromotionRewardByServerForManaged",
    "RefreshManagedPromotions",
]


def main():
    arg_parser = argparse.ArgumentParser(description="H5 포팅 검증 — C# 전처리문 구조 파서")
    arg_parser.add_argument("--platform", required=True,
                            choices=["WEBGL_PUREWEB", "WEBGL_TOSS", "WEBGL_LIVE_VER"])
    arg_parser.add_argument("--vocab", default="Docs/porting/PORTING_VOCAB.md")
    arg_parser.add_argument("--scripts", action="append", default=None, metavar="PATH",
                            help="스크립트 폴더 경로. 여러 번 지정 가능 (기본: Assets/Scripts)")
    arg_parser.add_argument("--exceptions", default="Docs/porting/verify-exceptions.json")
    arg_parser.add_argument("--method", action="append", default=[], metavar="NAME")
    arg_parser.add_argument("--exclude", action="append", default=["HyperLane"], metavar="FRAGMENT")
    arg_parser.add_argument("--mode", choices=["verify", "scan-void", "scan-callers", "check-editor-shadow"],
                            default="verify",
                            help="verify: 메서드 호출 가드 검증 (기본) / scan-void: WebGL 공백 체인 탐지 / "
                                 "scan-callers: 래퍼 호출부 역추적 / check-editor-shadow: 에디터 섀도잉 탐지")
    arg_parser.add_argument("--wrapper", action="append", default=None, metavar="PATH",
                            help="A 처리 완료 래퍼 파일. 여러 번 지정 가능 (scan-callers 모드)")
    arg_parser.add_argument("--files", action="append", default=None, metavar="PATH",
                            help="포터가 수정·추가한 파일. 여러 번 지정 가능 (check-editor-shadow 모드 필수)")
    args = arg_parser.parse_args()

    # ── check-editor-shadow 모드 — 포터 수정 파일만 검사 (원본 체인은 불변식 기준선) ──
    if args.mode == 'check-editor-shadow':
        if not args.files:
            print("⚠ --files 인자가 필요합니다. 포터가 수정·추가한 파일을 지정하세요.")
            sys.exit(1)
        target_files = []
        for file_str in args.files:
            file_path = Path(file_str)
            if file_path.exists():
                target_files.append(file_path)
            else:
                print(f"⚠ 파일을 찾을 수 없습니다: {file_str}")
        if not target_files:
            print("❌ 검사할 파일이 없습니다.")
            sys.exit(1)

        shadow_scanner = EditorShadowScanner(args.platform)
        for target in target_files:
            shadow_scanner.scan_file(target, str(target))

        print("=" * 62)
        print("에디터 섀도잉 검사 (check-editor-shadow)")
        print("=" * 62)
        print(f"  검사 파일 수: {len(target_files)}개")
        print(f"  섀도잉: {len(shadow_scanner.hits)}건 / 조건 평가 실패: {len(shadow_scanner.eval_failures)}건")
        for rel, lineno, cond in shadow_scanner.eval_failures:
            print(f"  EVAL_FAILED: {rel}:{lineno} 조건 평가 불가 — '{cond}' (수동 확인 필요)")
        for hit in shadow_scanner.hits:
            print(f"  EDITOR_SHADOWED: {hit.rel}:{hit.taken_line} '#if {hit.taken_cond}' 가 "
                  f"{hit.shadowed_line}행 '{hit.shadowed_cond}' 분기를 에디터에서 가로챔 "
                  f"→ 조건에 '&& !UNITY_EDITOR' 추가 필요")
        if shadow_scanner.hits:
            sys.exit(1)
        print("  ✅ 섀도잉 없음")
        sys.exit(0)

    # --scripts 는 여러 번 지정 가능 (SCRIPTS_PATH + EXTRA_PATHS 지원)
    if not args.scripts:
        args.scripts = ["Assets/Scripts"]

    cs_files_set: set = set()
    for path_str in args.scripts:
        p = Path(path_str)
        if not p.exists():
            print(f"⚠ 폴더를 찾을 수 없습니다: {path_str}")
            continue
        cs_files_set.update(
            f for f in p.rglob("*.cs")
            if not any(excl in str(f) for excl in args.exclude)
        )
    cs_files = sorted(cs_files_set)

    if not cs_files:
        print("❌ .cs 파일을 찾을 수 없습니다.")
        sys.exit(1)

    # ── scan-callers 모드 ─────────────────────────────────────────────────────
    if args.mode == 'scan-callers':
        if not args.wrapper:
            print("⚠ --wrapper 인자가 필요합니다. A 처리 완료 래퍼 파일을 지정하세요.")
            sys.exit(1)
        wrapper_files = [Path(p) for p in args.wrapper if Path(p).exists()]
        missing = [p for p in args.wrapper if not Path(p).exists()]
        for m in missing:
            print(f"⚠ 래퍼 파일을 찾을 수 없습니다: {m}")
        if not wrapper_files:
            sys.exit(1)

        classifier = ConditionClassifier(args.platform, webgl_generic_safe=True)
        scanner = CallerScanner(classifier)
        scanner.load_wrappers(wrapper_files)

        if not scanner._wrappers:
            print("⚠ 래퍼 파일에서 public 메서드를 찾지 못했습니다.")
            sys.exit(1)

        wrapper_rels: set = set()
        for wf in wrapper_files:
            try:
                wrapper_rels.add(str(wf.relative_to(Path("."))))
            except ValueError:
                wrapper_rels.add(str(wf))

        caller_hits = scanner.scan(cs_files, Path("."), wrapper_rels)

        print(f"\n{'='*60}")
        print(f"  H5 래퍼 호출부 역추적 — {args.platform}")
        print(f"  래퍼 클래스  : {', '.join(scanner._wrappers.keys())}")
        print(f"{'='*60}\n")

        if caller_hits:
            print("── ❌ CALLER_MISSING (래퍼 메서드 가드 없이 호출) ────────────")
            for h in caller_hits:
                print(f"  ❌ {h.rel}:{h.lineno} — {h.caller_var}.{h.method}()  [{h.wrapper_class}]")
            print()

        print(f"{'─'*60}")
        print(f"  스캔 파일 수     : {len(cs_files)}개")
        print(f"  래퍼 클래스      : {len(scanner._wrappers)}개")
        total_methods = sum(len(v) for v in scanner._wrappers.values())
        print(f"  추적 메서드 수   : {total_methods}개")
        print(f"  ❌ CALLER_MISSING: {len(caller_hits)}건")
        if not caller_hits:
            print(f"\n  ✅ CALLER_MISSING 없음")
        print(f"{'─'*60}\n")

        sys.exit(1 if caller_hits else 0)

    # ── scan-void 모드 ────────────────────────────────────────────────────────
    if args.mode == 'scan-void':
        classifier = ConditionClassifier(args.platform, webgl_generic_safe=True)
        void_hits = VoidScanner(classifier).scan(cs_files, Path("."))

        print(f"\n{'='*60}")
        print(f"  H5 WebGL 공백 스캔 — {args.platform}")
        print(f"{'='*60}\n")

        for sev, icon, label in [
            ('CONTROL_FLOW', '❌', '루프/yield 누락 — 프레임 정지 위험'),
            ('STATE_UNDEF',  '⚠️ ', 'UI 상태 미정의 — 씬 기본값 의존'),
            ('BEHAVIOR_GAP', 'ℹ️ ', '동작 누락 — 의도 확인 필요'),
        ]:
            hits = [h for h in void_hits if h.severity == sev]
            if hits:
                print(f"── {icon} {label} ──────────────────────────────────")
                for h in hits:
                    print(f"  {icon} {h.rel}:{h.lineno} — {h.cond}")
                print()

        print(f"{'─'*60}")
        print(f"  스캔 파일 수    : {len(cs_files)}개")
        ctrl  = sum(1 for h in void_hits if h.severity == 'CONTROL_FLOW')
        state = sum(1 for h in void_hits if h.severity == 'STATE_UNDEF')
        gap   = sum(1 for h in void_hits if h.severity == 'BEHAVIOR_GAP')
        print(f"  ❌ CONTROL_FLOW : {ctrl}건")
        print(f"  ⚠️  STATE_UNDEF  : {state}건")
        print(f"  ℹ️  BEHAVIOR_GAP : {gap}건")
        if not void_hits:
            print(f"\n  ✅ WebGL 공백 없음")
        print(f"{'─'*60}\n")

        sys.exit(1 if ctrl else (2 if void_hits else 0))

    # ── verify 모드 (기존 로직) ───────────────────────────────────────────────
    method_names = args.method or []
    if not method_names:
        vocab = parse_vocab(Path(args.vocab))
        for k in VOCAB_KEYS:
            method_names.extend(vocab.get(k, []))

    if not method_names:
        print("⚠ 검사할 메서드명이 없습니다. --method 또는 PORTING_VOCAB.md 확인")
        sys.exit(1)

    safe_exceptions = load_exceptions(Path(args.exceptions))

    print(f"\n{'='*60}")
    print(f"  H5 포팅 검증 — {args.platform}")
    print(f"  대상 메서드  : {', '.join(method_names)}")
    print(f"  예외 로그    : {len(safe_exceptions)}건 필터링")
    print(f"{'='*60}\n")

    classifier = ConditionClassifier(args.platform, webgl_generic_safe=True)
    file_parser = PreprocParser(classifier)
    pattern = build_pattern(method_names)

    safe_methods = DefinitionScanner(file_parser, pattern).scan(cs_files)
    result = CallScanner(file_parser, pattern, safe_methods, safe_exceptions).scan(cs_files, Path("."))

    if args.platform == "WEBGL_TOSS" and TOSS_HANDLER_METHODS:
        toss_classifier = ConditionClassifier("WEBGL_TOSS", webgl_generic_safe=False)
        toss_parser = PreprocParser(toss_classifier)
        toss_pattern = build_pattern(TOSS_HANDLER_METHODS)
        toss_safe = DefinitionScanner(toss_parser, toss_pattern).scan(cs_files)
        toss_result = CallScanner(toss_parser, toss_pattern, toss_safe, safe_exceptions).scan(cs_files, Path("."))
        result.definite.extend(toss_result.definite)
        result.ambiguous.extend(toss_result.ambiguous)
        result.filtered += toss_result.filtered
        result.def_filtered += toss_result.def_filtered
        result.definite.sort()
        result.ambiguous.sort()

    if result.definite:
        print("── ❌ 미처리 (가드 없음) ──────────────────────────────────────")
        for rel, lineno, method in result.definite:
            print(f"  ❌ {rel}:{lineno} — {method}()")
        print()

    if result.ambiguous:
        print("── ⚠️  확인 필요 (#elif UNITY_WEBGL 블록) ───────────────────────")
        for rel, lineno, method, dl in result.ambiguous:
            print(f"  ⚠️  {rel}:{lineno} — {method}()  [지시문:{dl}줄]")
        print()

    print(f"{'─'*60}")
    print(f"  스캔 파일 수   : {len(cs_files)}개")
    print(f"  ❌ 미처리      : {len(result.definite)}건")
    print(f"  ⚠️  확인 필요   : {len(result.ambiguous)}건")
    print(f"  ✅ 정의 분석   : {result.def_filtered}건 자동 처리")
    print(f"  ✅ 로그 필터링 : {result.filtered}건")

    if not result.definite and not result.ambiguous:
        print(f"\n  ✅ 이상 없음 — {args.platform} 처리 누락 없음")
    print(f"{'─'*60}\n")

    if result.ambiguous:
        print("💡 ⚠️ 항목 처리: pureweb-porter의 '검증 — verify-exceptions 기록' 단계 실행")
        print(f"   로그 파일: {args.exceptions}\n")

    if result.definite:
        sys.exit(1)
    elif result.ambiguous:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
