"""
scan-void 모드 — WebGL 공백(Void) 체인 탐지.

OTHER_NATIVE arm은 있지만 WEBGL arm도 #else도 없는 #if...#endif 블록,
즉 WebGL 빌드에서 통째로 실행되지 않는 구간을 찾는다.
PreprocParser/PreprocStack과 독립적으로 자체 스택을 관리하므로
verify/callers 모드의 흐름에 영향을 주지 않는다.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from h5_port_verify.core import ConditionClassifier, Frame, parse_preproc

_VOID_YIELD_RE = re.compile(r'\byield\b')
_VOID_STATE_RE = re.compile(r'\.SetActive\s*\(|\.enabled\s*=')
_VOID_LOOP_RE = re.compile(r'\bIEnumerator\b')


@dataclass
class VoidHit:
    rel: str
    lineno: int
    severity: str   # CONTROL_FLOW | STATE_UNDEF | BEHAVIOR_GAP
    cond: str


def _void_severity(body_lines: list, context_lines: list) -> str:
    body = '\n'.join(body_lines)
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
