#!/usr/bin/env bash
# H5 포팅 워크플로우 설치 — repo 파일을 ~/.claude 및 ~/github/.templates 로 심볼릭 링크.
# 편집은 이 repo 안에서만. git pull 하면 전 프로젝트에 즉시 반영(심볼릭이라).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
TEMPLATES_LINK="$HOME/github/.templates"

echo "▶ repo: $REPO"

# 1) claude/ 미러 → ~/.claude/ (파일 단위 심볼릭)
echo "▶ ~/.claude 심볼릭 링크"
while IFS= read -r src; do
  rel="${src#"$REPO"/claude/}"
  dst="$CLAUDE_DIR/$rel"
  mkdir -p "$(dirname "$dst")"
  # 기존이 실제 파일이면(심볼릭 아님) 백업
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    mv "$dst" "$dst.bak"
    echo "  ⚠ 기존 실파일 백업: $dst.bak"
  fi
  ln -sfn "$src" "$dst"
  echo "  ✓ $dst"
done < <(find "$REPO/claude" -type f)

# 2) templates → ~/github/.templates (디렉토리 통째 심볼릭)
echo "▶ ~/github/.templates 심볼릭 링크"
mkdir -p "$(dirname "$TEMPLATES_LINK")"
if [ -e "$TEMPLATES_LINK" ] && [ ! -L "$TEMPLATES_LINK" ]; then
  mv "$TEMPLATES_LINK" "$TEMPLATES_LINK.bak"
  echo "  ⚠ 기존 실폴더 백업: $TEMPLATES_LINK.bak"
fi
ln -sfn "$REPO/templates" "$TEMPLATES_LINK"
echo "  ✓ $TEMPLATES_LINK → $REPO/templates"

echo ""
echo "✅ 설치 완료. Claude Code에서 /reload-plugins 또는 재시작 후 사용."
echo "   업데이트: 이 repo에서 git pull (심볼릭이라 자동 반영)"
