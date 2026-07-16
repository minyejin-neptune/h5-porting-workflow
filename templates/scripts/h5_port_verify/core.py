"""
전처리문 파싱·분류 공통 코어.

verify / scan-void / scan-callers 모드가 공유하는 #if/#elif/#else/#endif
스택 관리와 조건 분류기를 담는다. check-editor-shadow 모드는 이 코어를
쓰지 않고 shadow_mode.py에서 독립적으로 조건을 불리언 평가한다.
"""

import json
import re
from dataclasses import dataclass
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


# ── 데이터 클래스 ────────────────────────────────────────────────────────────────

@dataclass
class Frame:
    cond_type: str
    directive_line: int
    in_else: bool = False


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
