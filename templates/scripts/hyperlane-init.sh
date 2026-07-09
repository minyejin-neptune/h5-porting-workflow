#!/usr/bin/env bash
# Hyperlane SDK 최초 셋업 — npm install + npx hyperlane init 표준 진입점
# 사용법: hyperlane-init.sh   (게임 프로젝트 루트에서 실행)
# exit: 0=완료, 1=설치/init 실패, 2=사전 점검 실패
set -uo pipefail

# 사전 점검 — 프로젝트 루트
if [ ! -f ProjectSettings/ProjectVersion.txt ]; then
  echo "⛔ STOP: 게임 프로젝트 루트가 아닙니다 (ProjectSettings/ProjectVersion.txt 없음)"
  exit 2
fi

echo "▶ npm install https://github.com/neptunez-dev/hyperlane-sdk.git"
npm install https://github.com/neptunez-dev/hyperlane-sdk.git
if [ $? -ne 0 ]; then
  echo "⛔ STOP: npm install 실패"
  exit 1
fi

echo "▶ npx hyperlane init"
npx hyperlane init
if [ $? -ne 0 ]; then
  echo "⛔ STOP: npx hyperlane init 실패"
  exit 1
fi

echo ""
echo "✅ hyperlane init 완료."
