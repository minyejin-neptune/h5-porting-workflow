#!/usr/bin/env bash
# H5 컴파일 체크 — Unity batchmode 실행 표준 진입점 (모든 워크플로우 문서는 이 스크립트를 호출한다)
# 사용법:
#   compile-check.sh <TOSS|PUREWEB|ANDROID>   CLI 모드 — 게임 프로젝트 루트에서 실행
#   compile-check.sh                          hook 모드 — PostToolUse hook. stdin으로 tool JSON을 받는다
#                                             (hook은 인자를 받을 수 없어 플랫폼을 .porting-context에서 읽는다)
# exit: 0=컴파일 통과, 1=컴파일 에러, 2=사전 점검 실패·판정 불가(미실행/불완전)
set -uo pipefail

HOOK_MODE=0
PLATFORM="${1:-}"

if [ $# -eq 0 ]; then
  HOOK_MODE=1
  INPUT=$(cat)
  FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
  case "$FILE" in
    *.cs) ;;
    *) exit 0 ;;
  esac
  CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
  [ -n "$CWD" ] && cd "$CWD" 2>/dev/null
  # hook은 모든 .cs 편집에 발화한다 — 게임 프로젝트가 아니면 관여하지 않는다
  [ -f ProjectSettings/ProjectVersion.txt ] || exit 0
  PLATFORM=""
  [ -f .porting-context ] && PLATFORM=$(tr -d '[:space:]' < .porting-context)
  [ -z "$PLATFORM" ] && PLATFORM="TOSS"
fi

# 판정 출력 — CLI 모드는 사람이 읽는 문구, hook 모드는 포터가 키로 삼는 신호를 낸다
# (신호 어휘 정의: templates/porter-rule.md § 컴파일 체크 자동화)
stop() {
  if [ "$HOOK_MODE" = 1 ]; then echo "⚠️ [COMPILE_REQUIRED] $*"; else echo "⛔ STOP: $*"; fi
  exit 2
}

case "$PLATFORM" in
  TOSS|PUREWEB|ANDROID) ;;
  *)
    [ "$HOOK_MODE" = 1 ] && stop ".porting-context의 플랫폼 값이 올바르지 않습니다: '$PLATFORM'"
    echo "사용법: compile-check.sh <TOSS|PUREWEB|ANDROID>"
    exit 2
    ;;
esac

# 사전 점검 1 — 프로젝트 루트
if [ ! -f ProjectSettings/ProjectVersion.txt ]; then
  stop "게임 프로젝트 루트가 아닙니다 (ProjectSettings/ProjectVersion.txt 없음)"
fi

# 사전 점검 2 — 프로젝트 Unity 버전 설치 여부
UNITY_VERSION=$(grep "m_EditorVersion:" ProjectSettings/ProjectVersion.txt | awk '{print $2}')
UNITY_BIN="/Applications/Unity/Hub/Editor/${UNITY_VERSION}/Unity.app/Contents/MacOS/Unity"
if [ -z "$UNITY_VERSION" ]; then
  stop "ProjectVersion.txt에서 Unity 버전을 읽지 못했습니다"
fi
if [ ! -x "$UNITY_BIN" ]; then
  stop "Unity $UNITY_VERSION 미설치 — Unity Hub에서 설치 후 다시 실행하세요 (없는 경로: $UNITY_BIN)"
fi

# 사전 점검 3 — 이 프로젝트가 에디터에 열려 있는지 (락 점유 기준 — 다른 프로젝트 열림은 무관)
if [ -f Temp/UnityLockfile ] && lsof Temp/UnityLockfile >/dev/null 2>&1; then
  stop "이 프로젝트가 에디터에서 열려 있어 batchmode 불가 — 에디터를 닫거나 Tools/H5/Compile Check 메뉴를 직접 실행하세요"
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
  stop "로그 파일이 생성되지 않았습니다 (Unity exit $UNITY_EXIT) — 실행 실패, 통과 아님"
fi

ERRORS=$(grep -E "error CS|^error " "$LOG_FILE" 2>/dev/null | sort -u)
if [ -n "$ERRORS" ]; then
  echo "$ERRORS"
  ERR_COUNT=$(echo "$ERRORS" | wc -l | tr -d ' ')
  if [ "$HOOK_MODE" = 1 ]; then
    echo "❌ [COMPILE_ERROR] 컴파일 에러 $ERR_COUNT건 ($PLATFORM) — 즉시 수정 필요. 로그: $LOG_FILE"
  else
    echo "❌ 컴파일 에러 $ERR_COUNT건 ($PLATFORM) — 로그: $LOG_FILE"
  fi
  exit 1
fi
if [ "$UNITY_EXIT" -ne 0 ]; then
  stop "에러 검출 0건이지만 Unity 종료 코드 $UNITY_EXIT — 판정 불가, 로그 확인 필요: $LOG_FILE"
fi

if [ "$HOOK_MODE" = 1 ]; then
  echo "✅ [COMPILE_OK] 컴파일 통과 ($PLATFORM)"
else
  echo "✅ 컴파일 정상 ($PLATFORM) — 로그: $LOG_FILE"
fi
exit 0
