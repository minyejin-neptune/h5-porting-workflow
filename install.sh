#!/usr/bin/env bash
# H5 포팅 워크플로우 설치 — repo의 claude/ 를 ~/.claude 로 심볼릭 링크.
# templates/ 는 심볼릭 없이 repo 경로를 직접 참조하므로,
# repo는 반드시 ~/github/h5-porting-workflow 에 clone 되어 있어야 한다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
EXPECTED="$HOME/github/h5-porting-workflow"

echo "▶ repo: $REPO"

# 0) clone 위치 확인 — 워크플로우가 이 경로를 직접 참조함
if [ "$REPO" != "$EXPECTED" ]; then
  echo "  ⚠ 경고: repo가 표준 위치가 아닙니다."
  echo "     현재: $REPO"
  echo "     기대: $EXPECTED"
  echo "     템플릿 참조(~/github/h5-porting-workflow/templates/...)가 안 맞아 깨질 수 있습니다."
  echo "     → $EXPECTED 로 clone 하길 권장."
fi

# 1) claude/ 미러 → ~/.claude/ (파일 단위 심볼릭)
echo "▶ ~/.claude 심볼릭 링크"
while IFS= read -r src; do
  rel="${src#"$REPO"/claude/}"
  dst="$CLAUDE_DIR/$rel"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    mv "$dst" "$dst.bak"
    echo "  ⚠ 기존 실파일 백업: $dst.bak"
  fi
  ln -sfn "$src" "$dst"
  echo "  ✓ $dst"
done < <(find "$REPO/claude" -type f)

echo ""
echo "✅ 설치 완료. Claude Code에서 /reload-plugins 또는 재시작 후 사용."
echo "   업데이트: 이 repo에서 git pull"
echo "   템플릿: $REPO/templates 를 직접 참조 (심볼릭 없음)"
