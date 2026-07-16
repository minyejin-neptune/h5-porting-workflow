"""
verify 모드 — 메서드 호출 가드 검증.

대상 메서드(광고/IAP/저장 등)가 플랫폼 가드 없이 호출되는 곳을 2-pass로 탐지한다.
Pass 1(DefinitionScanner)이 대상 플랫폼에서 접근 가능한 정의를 먼저 수집하고,
Pass 2(CallScanner)가 그 정의 집합과 예외 로그를 참조해 실제 이슈만 추린다.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from h5_port_verify.core import PreprocParser, is_definition_line


@dataclass
class ScanResult:
    definite: list = field(default_factory=list)   # [(rel, lineno, method)]
    ambiguous: list = field(default_factory=list)  # [(rel, lineno, method, directive_line)]
    filtered: int = 0
    def_filtered: int = 0


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


# ── PORTING_VOCAB.md 파싱 ──────────────────────────────────────────────────────

VOCAB_KEYS = ["AD_REWARDED_METHOD", "IAP_METHOD", "SAVE_METHOD"]

TOSS_HANDLER_METHODS = [
    "InitializeAppsInTossBannerAd",
    "AttachAppsInTossBannerAd",
    "DetachAppsInTossBannerAd",
    "ClaimPromotionRewardForGameForManaged",
    "ClaimPromotionRewardByServerForManaged",
    "RefreshManagedPromotions",
]


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
