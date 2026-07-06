#!/usr/bin/env bash
# H5 컴파일 체크 — Unity batchmode 실행 표준 진입점 (모든 워크플로우 문서는 이 스크립트를 호출한다)
# 사용법: compile-check.sh <TOSS|PUREWEB|ANDROID>   (게임 프로젝트 루트에서 실행)
# exit: 0=컴파일 통과, 1=컴파일 에러, 2=사전 점검 실패·판정 불가(미실행/불완전)
set -uo pipefail

PLATFORM="${1:-}"
case "$PLATFORM" in
  TOSS|PUREWEB|ANDROID) ;;
  *) echo "사용법: compile-check.sh <TOSS|PUREWEB|ANDROID>"; exit 2 ;;
esac

# 사전 점검 1 — 프로젝트 루트
if [ ! -f ProjectSettings/ProjectVersion.txt ]; then
  echo "⛔ STOP: 게임 프로젝트 루트가 아닙니다 (ProjectSettings/ProjectVersion.txt 없음)"
  exit 2
fi

# 사전 점검 2 — 프로젝트 Unity 버전 설치 여부
UNITY_VERSION=$(grep "m_EditorVersion:" ProjectSettings/ProjectVersion.txt | awk '{print $2}')
UNITY_BIN="/Applications/Unity/Hub/Editor/${UNITY_VERSION}/Unity.app/Contents/MacOS/Unity"
if [ -z "$UNITY_VERSION" ]; then
  echo "⛔ STOP: ProjectVersion.txt에서 Unity 버전을 읽지 못했습니다"
  exit 2
fi
if [ ! -x "$UNITY_BIN" ]; then
  echo "⛔ STOP: Unity $UNITY_VERSION 미설치 — Unity Hub에서 설치 후 다시 실행하세요"
  echo "        (없는 경로: $UNITY_BIN)"
  exit 2
fi

# 사전 점검 3 — 이 프로젝트가 에디터에 열려 있는지 (락 점유 기준 — 다른 프로젝트 열림은 무관)
if [ -f Temp/UnityLockfile ] && lsof Temp/UnityLockfile >/dev/null 2>&1; then
  echo "⛔ STOP: 이 프로젝트가 에디터에서 열려 있어 batchmode 불가 — 에디터를 닫거나 Tools/H5/Compile Check 메뉴를 직접 실행하세요"
  exit 2
fi

# 실행
if [ "$PLATFORM" = "ANDROID" ]; then
  LOG_FILE="/tmp/unity_android_compile.log"
  "$UNITY_BIN" -batchmode -quit -projectPath "$(pwd)" -buildTarget Android -logFile "$LOG_FILE"
  UNITY_EXIT=$?
else
  LOG_FILE="Docs/porting/compile_result.log"
  mkdir -p Docs/porting
  "$UNITY_BIN" -batchmode -quit -projectPath "$(pwd)" -buildTarget WebGL \
    -executeMethod CompileChecker.Run -customArgs "$PLATFORM" -logFile "$LOG_FILE"
  UNITY_EXIT=$?
fi

# batchmode 부수효과 되돌리기 — 빌드타겟 전환·아틀라스 재생성 잔여물 (컴파일 판정만 목적)
git checkout -- ProjectSettings/ProjectSettings.asset 2>/dev/null || true
git diff --name-only 2>/dev/null | grep '\.spriteatlas$' | xargs git checkout -- 2>/dev/null || true

# 판정 — 로그의 에러가 기준. 로그가 없으면 판정 불가(통과로 오판 금지)
if [ ! -f "$LOG_FILE" ]; then
  echo "⛔ STOP: 로그 파일이 생성되지 않았습니다 (Unity exit $UNITY_EXIT) — 실행 실패, 통과 아님"
  exit 2
fi

ERRORS=$(grep -E "error CS|^error " "$LOG_FILE" 2>/dev/null | sort -u)
if [ -n "$ERRORS" ]; then
  echo "$ERRORS"
  echo "❌ 컴파일 에러 $(echo "$ERRORS" | wc -l | tr -d ' ')건 ($PLATFORM) — 로그: $LOG_FILE"
  exit 1
fi
if [ "$UNITY_EXIT" -ne 0 ]; then
  echo "⛔ STOP: 에러 검출 0건이지만 Unity 종료 코드 $UNITY_EXIT — 판정 불가, 로그 확인 필요: $LOG_FILE"
  exit 2
fi
echo "✅ 컴파일 정상 ($PLATFORM) — 로그: $LOG_FILE"
exit 0
