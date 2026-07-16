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

이 파일은 CLI 진입점(argparse + 모드 dispatch)만 담당한다.
실제 검증 로직은 h5_port_verify/ 패키지에 모드별로 분리되어 있다:
  core.py         — 전처리문 파싱·조건 분류기 (verify/scan-void/scan-callers 공유)
  verify_mode.py  — verify 모드 (메서드 호출 가드 검증)
  void_mode.py    — scan-void 모드 (WebGL 공백 체인 탐지)
  callers_mode.py — scan-callers 모드 (래퍼 호출부 역추적)
  shadow_mode.py  — check-editor-shadow 모드 (에디터 분기 가로채기 탐지)
"""

import argparse
import sys
from pathlib import Path

from h5_port_verify.core import ConditionClassifier, PreprocParser, build_pattern, load_exceptions
from h5_port_verify.callers_mode import CallerScanner
from h5_port_verify.shadow_mode import EditorShadowScanner
from h5_port_verify.verify_mode import (
    TOSS_HANDLER_METHODS,
    VOCAB_KEYS,
    CallScanner,
    DefinitionScanner,
    parse_vocab,
)
from h5_port_verify.void_mode import VoidScanner


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
