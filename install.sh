#!/usr/bin/env bash
# H5 포팅 워크플로우 설치 — repo의 claude/ 를 ~/.claude 로 심볼릭 링크.
# templates/ 는 심볼릭 없이 repo 경로를 직접 참조하므로, 이 스크립트가
# 실제 clone 경로를 감지해 $H5PW_ROOT 환경변수로 셸 rc에 등록한다.
# clone 위치는 자유 — repo 폴더명만 h5-porting-workflow 여야 한다.
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "▶ repo: $REPO"

# 0) 폴더명 확인 — 워크플로우 문서가 이 이름을 전제로 $H5PW_ROOT를 참조함
if [ "$(basename "$REPO")" != "h5-porting-workflow" ]; then
  echo "  ⚠ 경고: repo 폴더명이 h5-porting-workflow가 아닙니다 (현재: $(basename "$REPO"))."
  echo "     템플릿 참조 문서들이 이 이름을 전제로 하므로 폴더명을 h5-porting-workflow로 맞추길 권장."
fi

# 1) $H5PW_ROOT 환경변수 등록 — clone 위치는 자유, 폴더명만 고정이면 어디서든 동작
RC_CANDIDATES=("$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile")
rc_found=0
for rc in "${RC_CANDIDATES[@]}"; do
  [ -f "$rc" ] || continue
  rc_found=1
  if grep -q '^export H5PW_ROOT=' "$rc" 2>/dev/null; then
    tmp="$(mktemp)"
    grep -v '^export H5PW_ROOT=' "$rc" > "$tmp"
    mv "$tmp" "$rc"
  fi
  echo "export H5PW_ROOT=\"$REPO\"" >> "$rc"
  echo "  ✓ \$H5PW_ROOT 등록: $rc"
done
if [ "$rc_found" -eq 0 ]; then
  echo "export H5PW_ROOT=\"$REPO\"" >> "$HOME/.profile"
  echo "  ✓ \$H5PW_ROOT 등록: $HOME/.profile"
fi

# 2) claude/ 미러 → ~/.claude/ (파일 단위 심볼릭)
if [ ! -d "$REPO/claude" ]; then
  echo "✗ 에러: $REPO/claude 디렉토리가 없습니다. repo가 손상되었거나 잘못된 위치에서 실행했을 수 있습니다." >&2
  exit 1
fi

echo "▶ ~/.claude 심볼릭 링크"
while IFS= read -r src; do
  rel="${src#"$REPO"/claude/}"
  dst="$CLAUDE_DIR/$rel"
  mkdir -p "$(dirname "$dst")"
  # 부모 디렉토리가 이미 repo를 가리키는 심볼릭 링크인 경우, $dst와 $src가
  # 물리적으로 같은 파일일 수 있다 — 이때 mv+ln을 그대로 하면 자기 자신을
  # 가리키는 심볼릭 링크가 만들어진다(실제로 발생했던 버그). 같은 파일이면 건너뛴다.
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    if [ "$(cd "$(dirname "$dst")" && pwd -P)/$(basename "$dst")" = "$(cd "$(dirname "$src")" && pwd -P)/$(basename "$src")" ]; then
      echo "  ↷ 이미 동일 파일(상위 디렉토리가 심볼릭) — 건너뜀: $dst"
      continue
    fi
    if [ -e "$dst.bak" ]; then
      echo "✗ 에러: 백업 대상이 이미 존재합니다: $dst.bak" >&2
      echo "   기존 .bak을 직접 확인 후 옮기거나 삭제하고 재실행하세요." >&2
      exit 1
    fi
    mv "$dst" "$dst.bak"
    echo "  ⚠ 기존 실파일 백업: $dst.bak"
  fi
  ln -sfn "$src" "$dst"
  echo "  ✓ $dst"
done < <(find "$REPO/claude" -type f)

echo ""
echo "✅ 설치 완료. 터미널 재시작(또는 셸 rc 재로드) 후 Claude Code 사용."
echo "   업데이트: 이 repo에서 git pull"
echo "   템플릿: \$H5PW_ROOT/templates 를 직접 참조 (심볼릭 없음, \$H5PW_ROOT=$REPO)"
