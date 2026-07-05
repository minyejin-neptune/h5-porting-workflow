---
description: 프로젝트 초기 설정 — CLAUDE.md · Docs/README.md · Editor 스크립트 복사 → CLAUDE.md 초기화 → FRAMEWORK_REFERENCE.md 생성
---

다음 순서로 실행해주세요.

## Step 1 — 템플릿 파일 연결

### 1-A. 복사 (프로젝트별로 내용이 달라지는 파일)

Bash로 실행하세요. `-n` 플래그로 기존 파일은 덮어쓰지 않습니다:

```bash
mkdir -p Docs Assets/Editor
cp -n ~/github/h5-porting-workflow/templates/CLAUDE_Porting.md ./CLAUDE.md \
  && echo "✓ CLAUDE.md 복사 완료" \
  || echo "⚠ CLAUDE.md 이미 존재 — 건너뜀 (덮어쓰려면 사용자에게 확인)"
cp -n ~/github/h5-porting-workflow/templates/README.md ./Docs/README.md \
  && echo "✓ Docs/README.md 복사 완료" \
  || echo "⚠ Docs/README.md 이미 존재 — 건너뜀 (덮어쓰려면 사용자에게 확인)"
```

### 1-B. Editor 스크립트 복사

Editor 스크립트는 프로젝트에 **복사**합니다 (심볼릭 링크 금지).
이유: 원격/CI 빌더엔 `~/github/h5-porting-workflow/templates`가 없어 심볼릭이면 dangling으로 깨진다. 실파일로 복사해야 프로젝트 git에 커밋되어 어디서든 빌드된다.
`.cs`만 복사하고 `.meta`는 Unity가 프로젝트 로컬에 생성합니다. 기존에 실제 파일이 있으면 덮어쓰지 않고 건너뜁니다:

```bash
copy_template() {
  local src="$1" dst="$2"
  if [ -f "$dst" ] && [ ! -L "$dst" ]; then
    echo "⚠ $dst 이미 실제 파일로 존재 — 건너뜀 (갱신하려면 사용자에게 확인)"
  else
    rm -f "$dst"   # 과거 심볼릭 링크가 있으면 제거 후 복사
    cp "$src" "$dst" && echo "✓ $dst → 복사 완료"
  fi
}

copy_template ~/github/h5-porting-workflow/templates/Editor/CompileChecker.cs      ./Assets/Editor/CompileChecker.cs
copy_template ~/github/h5-porting-workflow/templates/Editor/CompileResultWindow.cs ./Assets/Editor/CompileResultWindow.cs
copy_template ~/github/h5-porting-workflow/templates/Editor/TextureFormatSetter.cs ./Assets/Editor/TextureFormatSetter.cs
copy_template ~/github/h5-porting-workflow/templates/Editor/HLAddressableTool.cs   ./Assets/Editor/HLAddressableTool.cs
```

> 템플릿 갱신 시 각 프로젝트에서 재복사해야 반영됩니다 (복사 방식의 트레이드오프). 자주 바뀌면 회사 SDK 병합으로 대체 예정.

> **링크/복사 제외**: `~/github/h5-porting-workflow/templates/scripts/` 폴더는 프로젝트에 두지 않는다.
> 검증 스크립트는 템플릿에서 직접 실행한다:
> ```bash
> python ~/github/h5-porting-workflow/templates/scripts/h5-port-verify.py --platform WEBGL_PUREWEB
> ```

## Step 2 — CLAUDE.md 초기화

`init` 스킬을 실행하세요.
인자(args): `CLAUDE.md와 Docs/README.md를 읽고, 프로젝트 코드를 탐색해 CLAUDE.md의 빈 placeholder(Architecture Overview 등)를 채워주세요.`

## Step 3 — FRAMEWORK_REFERENCE.md 생성

코드베이스를 탐색해 `Docs/FRAMEWORK_REFERENCE.md`를 아래 규칙으로 작성하세요.

**Process**

1. `Docs/FRAMEWORK_REFERENCE.md`가 이미 존재하면 덮어쓰지 말고 업데이트하세요.
2. 진입점·매니저·시스템·유틸·헬퍼·재사용 API를 탐색하세요.
3. 모든 클래스/메서드는 grep/find로 존재 확인 후 작성하세요.
4. 구조 확인 후 파일을 작성하세요.

**Required Sections (8)**

1. **Entry Points** — scene load order, bootstrappers, initializers
2. **Core Systems** — gameplay managers, state machines, major controllers
3. **Data Layer** — save/load, UserData, server sync, ScriptableObjects
4. **UI Framework** — popup system, HUD, screen transitions, reusable UI components
5. **Utilities & Helpers** — extension methods, math utils, coroutine helpers
6. **Reusable APIs** — public methods intended for cross-system use (with signature + one-line desc)
7. **Platform Branches** — `#if WEBGL_TOSS` / `#if WEBGL_PUREWEB` split points
8. **Known Gotchas** — deprecated paths, shared variables with wide blast radius, non-obvious dependencies

**Formatting Rules**

- 개조식(bullet list), 문단 금지
- 열 맞춤 공백 금지
- 각 항목: `ClassName.MethodName(params)` — 한 줄 설명
- 간결하게 유지 (매 세션 읽히므로 토큰 비용 고려)
- 저장 경로: `Docs/FRAMEWORK_REFERENCE.md` (`Doc/` 아님)
