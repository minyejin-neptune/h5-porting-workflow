"""
check-editor-shadow 모드 — 에디터 분기 가로채기 탐지.

포팅으로 삽입된 WEBGL 분기가 에디터(WebGL 빌드타겟)에서 원본
UNITY_EDITOR 분기를 가로채는 체인을 탐지한다. core.py의
ConditionClassifier/PreprocStack과는 별개로, 조건을 직접 불리언
평가(eval_condition)하는 독립 로직을 쓴다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from h5_port_verify.core import parse_preproc

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
    taken_cond: str      # 에디터에서 실제로 타는 WEBGL 분기
    shadowed_line: int
    shadowed_cond: str   # 가로채인 원본 UNITY_EDITOR 분기


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
