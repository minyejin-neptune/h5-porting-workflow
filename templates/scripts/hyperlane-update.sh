#!/usr/bin/env bash
# Hyperlane SDK 갱신 — npm install(SDK 최신화) + npx hyperlane update 실행 후
# 프로젝트 전용 파일을 원복한다.
# 사용법: hyperlane-update.sh   (게임 프로젝트 루트에서 실행)
#
# 원복 정책:
#   무조건 자동 원복 (순수 데이터, SDK 기본값이 들어가면 항상 문제):
#     - Assets/HyperLane/Resources/HyperlaneConfig.asset
#     - Assets/WebGLTemplates/*/TemplateData/favicon.ico
#   diff 있으면 보여주고 사용자에게 원복 여부 확인 (로직 파일, SDK 개선사항 보존 가능성):
#     - Assets/WebGLTemplates/*/index.html
#     - Deploy/Toss/unity-webgl-wrapper/src/UnityCanvas.tsx
#   대상 아님: Deploy/Toss/unity-webgl-wrapper/index.html(update가 안 건드림), package-lock.json(정상 갱신)
#
# exit: 0=완료, 1=install/update 실패, 2=사전 점검 실패
set -uo pipefail

# 사전 점검 1 — 프로젝트 루트
if [ ! -f ProjectSettings/ProjectVersion.txt ]; then
  echo "⛔ STOP: 게임 프로젝트 루트가 아닙니다 (ProjectSettings/ProjectVersion.txt 없음)"
  exit 2
fi

# 사전 점검 2 — git 저장소
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "⛔ STOP: git 저장소가 아닙니다 — 원복 로직(git checkout)이 동작하지 않습니다"
  exit 2
fi

# 원복 후보 경로 수집 (존재하는 파일만)
AUTO_PATHS=()
[ -f "Assets/HyperLane/Resources/HyperlaneConfig.asset" ] && AUTO_PATHS+=("Assets/HyperLane/Resources/HyperlaneConfig.asset")
for f in Assets/WebGLTemplates/*/TemplateData/favicon.ico; do
  [ -f "$f" ] && AUTO_PATHS+=("$f")
done

ASK_PATHS=()
for f in Assets/WebGLTemplates/*/index.html; do
  [ -f "$f" ] && ASK_PATHS+=("$f")
done
[ -f "Deploy/Toss/unity-webgl-wrapper/src/UnityCanvas.tsx" ] && ASK_PATHS+=("Deploy/Toss/unity-webgl-wrapper/src/UnityCanvas.tsx")

# 사전 점검 3 — 원복 후보에 커밋 안 된 변경이 있으면 STOP (update+원복이 그 변경을 날려버림)
ALL_CANDIDATES=("${AUTO_PATHS[@]}" "${ASK_PATHS[@]}")
if [ ${#ALL_CANDIDATES[@]} -gt 0 ]; then
  DIRTY=$(git diff --name-only -- "${ALL_CANDIDATES[@]}")
  if [ -n "$DIRTY" ]; then
    echo "⛔ STOP: 원복 대상 파일에 커밋 안 된 변경이 있습니다 — 먼저 커밋하거나 stash 하세요:"
    echo "$DIRTY"
    exit 2
  fi
fi

echo "▶ npm install https://github.com/neptunez-dev/hyperlane-sdk.git (SDK 최신화)"
npm install https://github.com/neptunez-dev/hyperlane-sdk.git
if [ $? -ne 0 ]; then
  echo "⛔ STOP: npm install 실패"
  exit 1
fi

echo "▶ npx hyperlane update"
npx hyperlane update
if [ $? -ne 0 ]; then
  echo "⛔ STOP: npx hyperlane update 실패 — 원복 작업을 중단합니다"
  exit 1
fi

echo ""
echo "▶ 원복 처리 시작"

# 1) 무조건 자동 원복
for f in "${AUTO_PATHS[@]}"; do
  if ! git diff --quiet -- "$f"; then
    git checkout -- "$f"
    echo "✅ 원복: $f"
  fi
done

# 2) diff 있으면 보여주고 확인
for f in "${ASK_PATHS[@]}"; do
  if ! git diff --quiet -- "$f"; then
    echo ""
    echo "── $f 변경됨 ──"
    git diff -- "$f"
    read -r -p "이 파일을 원복할까요? [y/N] " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
      git checkout -- "$f"
      echo "✅ 원복: $f"
    else
      echo "⏭  유지 (SDK 최신본 적용): $f"
    fi
  fi
done

echo ""
echo "✅ hyperlane update + 원복 완료."
