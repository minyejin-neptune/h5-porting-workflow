---
description: 프로젝트 초기 설정 — CLAUDE.md · Docs/README.md · Editor 스크립트 복사 → CLAUDE.md 초기화 → FRAMEWORK_REFERENCE.md 생성
---

다음 순서로 실행해주세요.

## Step 0 — 기존 구조 감지 (붙이기 전 확인)

기존 프로젝트에 워크플로우를 붙이는 경우, 이미 있는 문서·폴더 구조를 먼저 파악해 **그 구조를 따른다** (템플릿 구조를 강요하지 않음).

```bash
ls -d Docs Doc 2>/dev/null || echo "문서 폴더 없음"   # Docs/ vs Doc/ vs 없음
find Docs -maxdepth 2 -type d 2>/dev/null              # 기존 Docs 하위 구조
ls CLAUDE.md 2>/dev/null && echo "CLAUDE.md 존재" || echo "CLAUDE.md 없음"
```

판정:
- **문서 폴더·CLAUDE.md 모두 없음** → Step 1의 템플릿 기본 구조(`Docs/design`·`Docs/porting` 등) 사용.
- **기존 문서 구조 있음** → 그 위치를 기준으로 삼는다. 이후 단계·에이전트가 확인된 경로에 저장(역기획서·포팅 산출물 위치). `Doc/`(단수) 등 다른 규칙이면 그걸 따르고 사용자에게 보고.
- **기존 CLAUDE.md 있음** → Step 1의 `cp -n`이 덮어쓰지 않으므로 포팅 전용 규칙(Build/Deploy·define·porting 문서 참조)이 빠져 있을 수 있다. 사용자에게 알리고 누락 규칙만 병합 안내.

## Step 1 — 템플릿 파일 연결

### 1-A. 복사 (프로젝트별로 내용이 달라지는 파일)

Bash로 실행하세요. `-n` 플래그로 기존 파일은 덮어쓰지 않습니다:

```bash
mkdir -p Docs Assets/Editor
cp -n $H5PW_ROOT/templates/CLAUDE_Porting.md ./CLAUDE.md \
  && echo "✓ CLAUDE.md 복사 완료" \
  || echo "⚠ CLAUDE.md 이미 존재 — 건너뜀 (덮어쓰려면 사용자에게 확인)"
cp -n $H5PW_ROOT/templates/README.md ./Docs/README.md \
  && echo "✓ Docs/README.md 복사 완료" \
  || echo "⚠ Docs/README.md 이미 존재 — 건너뜀 (덮어쓰려면 사용자에게 확인)"
```

### 1-B. Editor 스크립트 복사

Editor 스크립트는 프로젝트에 **복사**합니다 (심볼릭 링크 금지).
이유: 원격/CI 빌더엔 `$H5PW_ROOT/templates`가 없어 심볼릭이면 dangling으로 깨진다. 실파일로 복사해야 프로젝트 git에 커밋되어 어디서든 빌드된다.
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

copy_template $H5PW_ROOT/templates/Editor/CompileChecker.cs      ./Assets/Editor/CompileChecker.cs
copy_template $H5PW_ROOT/templates/Editor/CompileResultWindow.cs ./Assets/Editor/CompileResultWindow.cs
copy_template $H5PW_ROOT/templates/Editor/TextureFormatSetter.cs ./Assets/Editor/TextureFormatSetter.cs
copy_template $H5PW_ROOT/templates/Editor/FontReplaceTool.cs     ./Assets/Editor/FontReplaceTool.cs

# HLAddressableTool.cs는 Addressables 패키지가 없으면 컴파일 오류가 나므로, 패키지가 있을 때만 복사한다.
if grep -q "com.unity.addressables" Packages/manifest.json 2>/dev/null; then
  copy_template $H5PW_ROOT/templates/Editor/HLAddressableTool.cs ./Assets/Editor/HLAddressableTool.cs
else
  echo "⏭ HLAddressableTool.cs 건너뜀 — Packages/manifest.json에 com.unity.addressables 없음"
fi
```

> 템플릿 갱신 시 각 프로젝트에서 재복사해야 반영됩니다 (복사 방식의 트레이드오프). 자주 바뀌면 회사 SDK 병합으로 대체 예정.

> **링크/복사 제외**: `$H5PW_ROOT/templates/scripts/` 폴더는 프로젝트에 두지 않는다.
> 검증 스크립트는 템플릿에서 직접 실행한다:
> ```bash
> python $H5PW_ROOT/templates/scripts/h5-port-verify.py --platform WEBGL_PUREWEB
> ```

## Step 2 — CLAUDE.md 초기화 (`Project-Specific Settings` 채우기)

**Claude Code에 기본 내장된 전역 `init` 스킬**(코드베이스를 탐색해 CLAUDE.md를 채우는 표준 기능 — h5-porting-workflow가 자체 정의한 스킬이 아니다)을 실행하세요. 인자로 아래 지시를 전달합니다:

> "CLAUDE.md와 Docs/README.md를 읽고, 프로젝트 코드를 탐색해 CLAUDE.md 상단 `## Project-Specific Settings` 섹션을 실제 프로젝트에 맞게 채우거나 없는 항목은 삭제하세요. 추론 금지 — 코드에서 확인한 것만 기재, 확인 못 하면 '확인 필요'로 남기고 사용자에게 보고."

각 하위 항목 검증 방법 (grep의 `--include` 글롭은 반드시 따옴표 — zsh에서 unquoted면 에러):

- **프로젝트 요약** — 진입점·게임 성격 코드를 탐색해 한 줄 설명 작성 (필요 시 `.md/PROJECT.md`)
- **커스텀 빌드 진입점** — 프로젝트 자체 빌드 메뉴(예: `Xxx/Build/`)는 SDK 빌드 스크립트(Tapjoy·BuildReport 등)와 섞여 grep만으론 판별 불가. **porting-scan(STEP 2)의 "자체 빌드 스크립트" 결과로 확정**하고, 그 전이면 "확인 필요"로 남긴다.
- **배포 명령** — `find . -maxdepth 5 -name "deploy*.sh" 2>/dev/null` → 히트면 실제 경로로 교체, 0건이면 그 줄 삭제
- **프로젝트 전용 define** — `grep -rhoE "#if [A-Z][A-Z0-9_]+" Assets/Scripts --include="*.cs" | grep -vE "UNITY_|WEBGL_|ENABLE_LOG" | sort -u` (또는 `ProjectSettings/ProjectSettings.asset`의 `scriptingDefineSymbols`) → 후보 나열(서드파티 SDK define 섞일 수 있음) → 실제 프로젝트가 쓰는 것만 확정하고 예시(`AVOEX_*`)는 교체/삭제. 불명확하면 "확인 필요"

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
