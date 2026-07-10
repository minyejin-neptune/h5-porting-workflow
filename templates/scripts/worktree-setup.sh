#!/usr/bin/env bash
# 워크트리 병렬 작업 생성 표준 진입점 (모든 워크플로우 문서는 이 스크립트를 호출한다)
# 사용법: worktree-setup.sh <worktree-이름> <브랜치명>   (게임 프로젝트 루트에서 실행)
# 성공 시 표준출력에 새 worktree 절대경로 1줄만 출력한다 — 호출자는 그 값으로 반드시 cd한다.
# exit: 0=성공, 2=사전 점검 실패
set -euo pipefail

NAME="${1:-}"
BRANCH="${2:-}"

if [ -z "$NAME" ] || [ -z "$BRANCH" ]; then
  echo "사용법: worktree-setup.sh <worktree-이름> <브랜치명>" >&2
  exit 2
fi

if [ ! -f ProjectSettings/ProjectVersion.txt ]; then
  echo "⛔ STOP: 게임 프로젝트 루트가 아닙니다 (ProjectSettings/ProjectVersion.txt 없음)" >&2
  exit 2
fi

MAIN_DIR="$(pwd)"

git worktree add "../${NAME}" -b "${BRANCH}" >&2

WORKTREE_DIR="$(cd "../${NAME}" && pwd)"

# Library 복사 — 재임포트 방지(없으면 Unity가 전체 에셋을 처음부터 다시 임포트해 매우 느림).
# 반드시 복사한다 — 심볼릭 링크 금지. Temp까지 같이 공유되면 Temp/UnityLockfile도 공유돼
# 다른 worktree(또는 메인 프로젝트)에서 에디터가 열려 있을 때 이 worktree에서도
# "열려있음"으로 오판되어 컴파일 배치가 막힌다. Temp는 복사하지 않는다 — Unity가
# worktree마다 새로 만들어야 락 파일이 독립적으로 관리된다.
if [ -d "${MAIN_DIR}/Library" ]; then
  cp -R "${MAIN_DIR}/Library" "${WORKTREE_DIR}/Library" >&2
fi

echo "${WORKTREE_DIR}"
