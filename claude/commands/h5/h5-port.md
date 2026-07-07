---
description: H5 포팅 오케스트레이터 — STEP 0~4 전체 파이프라인(인코딩·스캔·검증·포터·최종검증) 순차 실행
---

# H5 포팅 오케스트레이터

$ARGUMENTS 프로젝트의 H5 포팅을 순서대로 실행한다.

각 단계 완료 후 결과를 보여주고 다음 단계로 진행한다.

---

## 인자 파싱

`$ARGUMENTS`로 시작 스텝 또는 플랫폼을 지정할 수 있다. 생략하면 STEP 0부터 전체 실행.

| 형식 | 동작 |
|---|---|
| (없음) | STEP 0부터 전체 실행 |
| `2` | STEP 2(프로젝트 분석)부터 시작 |
| `3` | STEP 3(포터 선택)부터 시작 |
| `toss` | STEP 3, toss 포터 바로 실행 |
| `pureweb` | STEP 3, pureweb 포터 바로 실행 |

**스텝 점프 시 필수 처리**: 어느 스텝에서 시작하든 아래 순서로 먼저 실행한다.
1. 아래 VOCAB 변수 매핑 컨벤션 섹션을 읽는다
2. `Docs/porting/PORTING_VOCAB.md`가 있으면 읽어 플레이스홀더를 확정한다
3. 지정된 스텝으로 점프한다

---

## 진입 — 후속 모드 감지 (재실행)

인자 파싱 전에, 이 프로젝트에 이미 열린 포팅 이슈가 있는지 확인한다:

```bash
gh issue list --state open --search "[포팅]" --json number,title 2>/dev/null
```

- 결과 없음(또는 gh remote 없음) → 일반 실행 — 인자 파싱대로 진행.
- **open 포팅 이슈 있음 → 후속 모드**:
  1. STEP 0~2(초기 설정·인코딩·스캔·검증)는 재실행하지 않는다 — 이미 완료된 프로젝트다.
  2. 이슈 본문에서 미체크(`- [ ]`) 항목을 추출한다 — `## 사람 준비 항목`과 `## 확인 필요 / 미확정` 두 섹션 모두.
  3. 추출한 항목만 AskUserQuestion으로 재질문한다 (여전히 미확정이면 미확정 유지 허용).
  4. 확정된 답변은 `gh issue edit`로 이슈 본문에 반영한다 (`[ ]` → `[x]` + 확정값).
  5. 새로 확정된 항목이 1건 이상이면 STEP 3-C로 가서 포터를 **부분 수정 모드**로 재호출한다 (prompt 형식은 STEP 3-C 참조). 확정된 항목이 없으면 "미확정 항목 변동 없음 — 종료"를 출력하고 끝낸다.
  6. 포터 완료 후 STEP 4-A의 기존 종료 처리(검증 통과 + 미확정 없음 → close)를 그대로 적용한다.

---

## 커밋 원칙

**각 STEP이 파일을 생성·수정했으면 완료 후 반드시 커밋한다.** 커밋 없이 다음 STEP으로 넘어가지 않는다 — 다음 STEP 시작 전 `git status`로 미커밋 변경사항이 없는지 확인한다. STEP별 커밋 대상·메시지는 각 STEP 본문에 명시돼 있다(STEP 0-C, STEP 1, STEP 1-A, STEP 1-C, STEP 2-B-commit 등). 포터(toss-porter/pureweb-porter) 실행 중 커밋은 포터 자체 지침(`## 체크리스트 관리`)을 따른다.

---

## STEP 0 — 프로젝트 초기 설정

`~/.claude/commands/project/porting-init.md` 파일을 읽고 해당 지침에 따라 실행한다.

완료 후 아래 절차를 순서대로 실행한다.

### 0-A. 브랜치 확인

```bash
git branch --show-current
```

브랜치명이 `플랫폼/버전` 형식(예: `toss/v1.0`, `pureweb/1.2.3`)인지 확인한다.
버전 값은 Unity Editor의 `Player Settings` → `Version`(또는 `ProjectSettings/ProjectSettings.asset`의 `bundleVersion`)에서 확인한다 — 임의로 지어내지 않는다.

- 형식이 맞으면 → 0-B로 진행
- 형식이 맞지 않으면(예: `main`, `master`, 빈 값) → 아래 메시지를 출력하고 **사용자가 확인할 때까지 대기**:

```
⚠️ 현재 브랜치: {브랜치명}

포팅 커밋 전에 작업 브랜치(플랫폼/버전 형식)로 전환해 주세요.
전환 완료 후 계속 진행하겠습니까?
```

AskUserQuestion으로 확인 후 진행한다.

### 0-B. Addressables 패키지 확인

porting-init 단계에서 `HLAddressableTool.cs`는 Addressables 패키지가 있을 때만 복사된다(없으면 컴파일 오류가 나므로 자동으로 건너뜀). 패키지 상태와 실제 파일 존재 여부가 일치하는지 확인한다.

```bash
grep -q "com.unity.addressables" Packages/manifest.json \
  && echo "ADDRESSABLES_OK" \
  || echo "ADDRESSABLES_MISSING"
ls Assets/Editor/HLAddressableTool.cs 2>/dev/null && echo "FILE_EXISTS" || echo "FILE_ABSENT"
```

| 패키지 | 파일 | 판정 |
|---|---|---|
| OK | EXISTS | 정상 → 0-C로 진행 |
| MISSING | ABSENT | 정상(porting-init이 건너뜀) → 0-C로 진행 |
| MISSING | EXISTS | 과거 복사분 잔존 — 컴파일 오류 유발 가능. 아래 AskUserQuestion |
| OK | ABSENT | porting-init 미실행/실패 추정. 아래 AskUserQuestion |

- `MISSING` + `EXISTS` → AskUserQuestion:
  > "Addressables 패키지가 없는데 `HLAddressableTool.cs`가 이미 존재합니다(과거 복사분으로 추정). 컴파일 오류를 유발할 수 있습니다.
  > - 패키지 설치 후 계속 → Unity Editor에서 `com.unity.addressables`를 설치한 뒤 알려주세요.
  > - 파일 삭제 후 계속 → `rm -f Assets/Editor/HLAddressableTool.cs Assets/Editor/HLAddressableTool.cs.meta`"
- `OK` + `ABSENT` → AskUserQuestion:
  > "Addressables 패키지는 있는데 `HLAddressableTool.cs`가 없습니다. porting-init에서 복사가 누락된 것으로 보입니다.
  > - 다시 복사 → `cp ~/github/h5-porting-workflow/templates/Editor/HLAddressableTool.cs ./Assets/Editor/HLAddressableTool.cs`
  > - 건너뛰고 계속"

### 0-C. STEP 0 산출물 커밋

STEP 0에서 생성·수정된 파일을 커밋한다.

```bash
# 존재하는 파일만 스테이징한다 (없는 .meta·미생성 문서는 건너뜀)
for path in CLAUDE.md Docs/README.md Docs/FRAMEWORK_REFERENCE.md \
    Assets/Editor/CompileChecker.cs Assets/Editor/CompileChecker.cs.meta \
    Assets/Editor/CompileResultWindow.cs Assets/Editor/CompileResultWindow.cs.meta \
    Assets/Editor/TextureFormatSetter.cs Assets/Editor/TextureFormatSetter.cs.meta \
    Assets/Editor/HLAddressableTool.cs Assets/Editor/HLAddressableTool.cs.meta; do
  [ -e "$path" ] && git add "$path"
done
git status --short
```

`git status`로 스테이징 목록을 확인한 뒤 커밋한다:

```bash
git commit -m "[문서] 포팅 초기 설정 — CLAUDE.md·FRAMEWORK_REFERENCE.md·Editor 툴 추가"
```

커밋 성공 후 STEP 1로 진행한다.

---

## VOCAB 변수 매핑 컨벤션

플레이스홀더 전체 정의는 `porting-scan.md`의 VOCAB 템플릿(`PORTING_VOCAB.md` 생성 형식)이 유일한 소스다 — 여기서 재정의하지 않는다. toss-porter·pureweb-porter는 생성된 `PORTING_VOCAB.md`를 직접 읽어 그 파일의 `플레이스홀더` 열을 참조하므로 이 표를 보지 않는다.

h5-port.md 본문이 직접 사용하는 플레이스홀더만 아래에 남긴다:

| 플레이스홀더 | PORTING_VOCAB.md 행 | 확정 방법 |
|---|---|---|
| `{GAME_INIT_METHOD}` | 게임 진입점 | PORTING_VOCAB.md 게임 진입점 행 |
| `{ASSET_COUNTS}` | 에셋 현황 | PORTING_VOCAB.md 에셋 현황 행 |
| `{SCRIPTS_PATH}` | — | NATIVE_BASELINE.md 헤더 `스크립트 경로:` |

---

## STEP 1 — EUC-KR 인코딩 검사 및 변환

Assets 하위 `.cs` 파일 중 UTF-8이 아닌 파일을 탐지한다.

```bash
python3 -c "
import os
problems = []
for root, dirs, files in os.walk('Assets'):
    dirs[:] = [d for d in dirs if d not in ['HyperLane']]
    for f in files:
        if not f.endswith('.cs'):
            continue
        path = os.path.join(root, f)
        try:
            open(path, encoding='utf-8').read()
        except UnicodeDecodeError:
            problems.append(path)
for p in problems:
    print(p)
"
```

- 탐지 결과 없음 → "✅ 인코딩 이상 없음" 출력 후 STEP 2로
- 탐지된 파일 있음 → 목록을 사용자에게 보여주고 변환 진행 여부 확인 후:

```bash
# 파일별 EUC-KR → UTF-8 변환 (탐지된 파일 각각 실행)
iconv -f EUC-KR -t UTF-8 "{파일경로}" -o "{파일경로}.utf8" \
  && mv "{파일경로}.utf8" "{파일경로}" \
  && echo "✓ {파일경로}" \
  || { echo "✗ 변환 실패: {파일경로}"; rm -f "{파일경로}.utf8"; }
```

**변환 후 — 한글 깨짐 확인 (필수)**: iconv 성공(exit 0)은 인코딩 변환 자체의 성공일 뿐, 원본이 실제로 EUC-KR이었는지는 보장하지 않는다(예: 이미 깨진 파일, CP949 등 다른 인코딩이면 문자가 다른 형태로 깨질 수 있다). 변환된 파일마다 한글이 포함된 라인을 샘플로 출력해 사용자에게 확인받는다:

```bash
grep -n "[가-힣]" "{파일경로}" | head -5
```

출력된 한글이 정상적으로 읽히는지 사용자에게 확인하고, 깨진 문자가 보이면 원본 인코딩을 재확인한다(예: `file -i "{파일경로}"` 또는 `iconv -f CP949`로 재시도).

**변환 완료 후 커밋 (필수)** — 변환한 파일만 스테이징한다:

```bash
git add {변환한 .cs 파일 목록}
git commit -m "[공통] EUC-KR → UTF-8 인코딩 변환"
```

---

## STEP 1-A — Android 플랫폼 컴파일 확인

포팅 전 Android 빌드 타겟 기준으로 컴파일이 정상인지 확인한다.
**오류가 있으면 사용자 결정 없이 STEP 1-B로 넘어가지 않는다.**

컴파일 실행과 **같은 응답에서** `Agent 도구(subagent_type: "sdk-list-analyzer")`를 백그라운드로 실행한다 — 아래 오류 분류에서 외부 SDK 목록이 필요하다. 에이전트는 BASELINE 존재·기존 산출물 신선도를 스스로 판정하므로(에이전트 STEP 0) 조건 분기 없이 항상 호출한다.

```bash
bash ~/github/h5-porting-workflow/templates/scripts/compile-check.sh ANDROID
```

사전 점검(버전 미판독·미설치·이 프로젝트 에디터 열림)과 판정은 스크립트에 내장되어 있다.

출력이 `⛔ STOP`이면 미실행·판정 불가이므로, 안내대로 조치될 때까지 STEP 1-B로 넘어가지 않는다.
`✅`면 STEP 1-B로 진행하고, `❌`(에러 목록 출력)면 아래 분류로 진행한다.

오류가 있으면 분류해서 사용자에게 보고한다.

**분류 시작 조건**: 컴파일 로그와 `Docs/porting/.sdk-list.md`(BASELINE 존재 케이스면 NATIVE_BASELINE.md `## 외부 SDK 목록`)가 **모두 준비된 후** 시작한다 — 에이전트가 아직 실행 중이면 완료를 기다린다. 에이전트가 실패했으면 소속 판별 없이 임의 분류하지 말고 사용자에게 보고 후 대기한다.

**분류 절차 — 못 찾은 심볼의 소속 판별** (에러 코드는 1차 필터일 뿐, 소속이 분류를 결정한다)

1. 오류 라인에서 못 찾은 심볼(타입·네임스페이스)을 추출한다 (`CS0246`/`CS0234` 등).
2. 프로젝트 코드에서 정의를 검색한다:
   ```bash
   grep -rnE "(class|struct|interface|enum) {심볼}\b" Assets --include="*.cs" 2>/dev/null | grep -v "Assets/HyperLane/"
   ```
3. 판별해 분류한다 — 오류 1건은 정확히 한 분류로 귀결한다:

| 판별 결과 | 분류 |
|---|---|
| 정의가 프로젝트 `.cs`에 있음 | 기타 — 참조·전처리(define) 문제 (파일은 있음) |
| 정의 없음 + 심볼이 외부 SDK 목록의 SDK·네임스페이스·폴더 소속 | SDK 문제 |
| 정의 없음 + SDK 목록에도 없음 | 파일 누락 — 정의했어야 할 스크립트 부재 |
| `CS0246`/`CS0234` 외 (문법 오류 등) | 기타 |

보고 형식:

```
⚠️ Android 컴파일 오류 발견

[파일 누락 (N건)]
- Assets/Scripts/Shop.cs:20 — error CS0246: 'InventoryManager' not found — 프로젝트 정의·SDK 목록 모두 없음
...

[SDK 문제 (N건)]
- Assets/Scripts/AdManager.cs:12 — error CS0246: 'GoogleMobileAds' not found — SDK 목록 대조: 광고 SDK 소속
...

[기타 (N건)]
- ...
```

각 분류별로 AskUserQuestion으로 처리 방안을 확인한다:

- **파일 누락**: "누락된 파일을 추가하시겠습니까, 아니면 해당 참조를 제거·주석 처리하시겠습니까?"
- **SDK 문제**: "SDK를 재설치하시겠습니까, 아니면 해당 SDK를 포팅 범위에서 제외하고 진행하시겠습니까?"
- **기타**: "직접 수정하시겠습니까?"

사용자가 수정을 선택하면 조치 완료 후 컴파일을 재실행해 오류가 사라졌는지 확인한다.
모든 분류에서 처리가 완료(수정 또는 의도적 제외 결정)된 후 STEP 1-B로 진행한다.

**수정한 내용이 있으면 STEP 1-B로 넘어가기 전 커밋한다** — `git status`로 변경 파일을 확인 후:

```bash
git add {수정한 파일 목록}
git commit -m "[수정] Android 컴파일 오류 수정"
```

---

## STEP 1-B — PostToolUse Hook 설정 확인

포팅 중 `.cs` 파일 수정 시마다 자동 컴파일 체크가 실행되려면 hook이 필요하다.

```bash
cat ~/.claude/settings.json 2>/dev/null | grep -A3 "PostToolUse\|CompileChecker" || echo "NOT_FOUND"
```

- hook 있음 → STEP 1-C로
- **hook 없음** → AskUserQuestion:

> "`.cs` 파일 수정 시 자동 컴파일 체크를 위한 PostToolUse hook이 설정되어 있지 않습니다.
> Claude Code 설정(`~/.claude/settings.json`)에 아래 hook을 추가하면 코드 수정 후 즉시 오류를 감지할 수 있습니다.
> 지금 추가할까요?
> - 예 → 아래 설정 안내
> - 아니오 → 포팅 중 수동으로 **Tools/H5/Compile Check** 메뉴를 직접 실행해야 합니다. 계속 진행합니다."

> hook 설정 방법: Claude Code 설정(`~/.claude/settings.json`) → PostToolUse 항목에 `.cs` 파일 수정 시 컴파일 체크 명령 추가.
> 설정 방법을 모르면 `/help`에서 hooks 관련 문서를 참고하거나, 사용자에게 직접 설정 요청 후 계속 진행한다.

---

## STEP 1-C — HyperLane SDK 설치 확인

```bash
ls Assets/HyperLane/ 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"
```

- INSTALLED → STEP 2로
- NOT_INSTALLED → AskUserQuestion으로 확인:

> "HyperLane SDK가 설치되어 있지 않습니다. 설치 후 진행할까요?"
> - 설치하겠습니다 → 아래 **설치 절차**대로 안내. 완료되면 알려달라고 안내. 확인 후 STEP 2로.
> - 설치 없이 진행 → 이후 분석 및 포팅에서 HLSDK 연동 불가 상태로 진행. NATIVE_BASELINE.md 프로젝트 정보 `HyperLane SDK` 행에 "⚠️ 미설치" 기록 (scan 생성 전이면 scan에게 전달).

**설치 절차** (Unity Editor 임포트 방식이 아니라 npm CLI 방식 — 출처: [README.md](https://github.com/neptunez-dev/hyperlane-sdk/blob/main/README.md)):

```bash
# 1. 프로젝트 루트(Assets/가 있는 위치)에서 실행
npm install https://github.com/neptunez-dev/hyperlane-sdk.git

# 2. 엔진(Unity) 자동 감지 후 공통 템플릿 복사 — Assets/HyperLane/, Packages/manifest.json UPM 의존성 등
npx hyperlane init
```

- 토스처럼 게임 외부 wrapper 프로젝트가 필요한 플랫폼은 추가로 `npx hyperlane setup toss` 실행 (대화형은 `npx hyperlane setup`). 셋업 중 `npm create vite@latest`의 `Install with npm and start now?` 질문에는 **반드시 `No`** 선택 — `Yes` 선택 시 dev server가 떠서 셋업이 멈춘다.
- PureWeb만 쓰는 경우 `init`까지로 끝.
- `npm install` 산출물(`node_modules/`, `package-lock.json`, `package.json`)은 SDK CLI 자체가 요구하는 정상 산출물이다 — Unity 프로젝트라고 지우지 않는다(`init`이 `.gitignore`에 `node_modules/`, `Build/`를 자동 추가).

**업데이트 절차** (이미 셋업된 프로젝트에서 SDK 코드만 최신화 — `init`/`setup` 재실행 불필요):

```bash
npm install https://github.com/neptunez-dev/hyperlane-sdk.git   # 최신 커밋 재설치 (URL 명시 필수 — 생략 시 package-lock 고정본 유지됨)
npx hyperlane update                                              # Assets/HyperLane/, WebGLTemplates/, wrapper 파일 등 SDK 관리 파일 갱신
```

- `HyperlaneConfig.asset`, `granite.config.ts`, wrapper의 `package.json`/`node_modules`, 사용자 추가 파일은 `update`가 덮어쓰지 않음.
- 특정 버전 고정: `npm install https://github.com/neptunez-dev/hyperlane-sdk.git#v1.0.0` (태그) 또는 `#커밋해시`.

**설치/업데이트 완료 후 커밋 (필수)** — `git status`로 SDK가 추가·수정한 파일을 확인 후 스테이징한다(`node_modules/`·`Build/`는 `.gitignore` 처리되어 제외됨):

```bash
git status
git add Assets/HyperLane Packages/manifest.json package.json package-lock.json
# 토스 wrapper setup을 실행한 경우 wrapper 디렉토리도 함께 add
git commit -m "[공통] HyperLane SDK 설치"
```

---

## STEP 2 — 프로젝트 분석

포팅 작업 전 필요한 모든 분석을 이 단계에서 완료한다.
하위 단계를 순서대로 실행한다.

### 2-A. porting-scan [직접 실행]

`~/.claude/commands/h5/porting-scan.md` 파일을 읽고 해당 지침에 따라 실행한다.
인자: $ARGUMENTS

### 2-B. porting-scan-verify [2-A 완료 후]

`~/.claude/commands/h5/porting-scan-verify.md` 파일을 읽고 해당 지침에 따라 실행한다.
단, porting-scan-verify.md의 VERIFY-COMPILE 항목(안내 출력)은 실행하지 않는다. 컴파일 체크는 STEP 3 직전에 직접 실행한다.

### 2-B-commit. 분석 산출물 커밋 [2-B 완료 후]

2-A~2-B에서 생성·수정된 분석 파일을 커밋한다.

```bash
git add Docs/porting/NATIVE_BASELINE.md Docs/porting/PORTING_VOCAB.md \
        Docs/porting/pureweb-checklist.md Docs/porting/toss-checklist.md
git status --short
```

스테이징 확인 후 커밋한다:

```bash
git commit -m "[문서] 포팅 분석 완료 — NATIVE_BASELINE·VOCAB·체크리스트 2종 생성"
```

**[2-B-commit 완료 후] 광고 중 게임 중지 확인**

PORTING_VOCAB에 `게임중지: 확인 필요`로 기록된 항목이 있으면 AskUserQuestion으로 확인한다. PORTING_VOCAB의 탐색 결과(TimeScale·Coroutine 파일 목록)만으로 판단 근거를 제시한다:

> "광고(전면/보상형)가 표시되는 동안 게임을 일시 정지해야 하나요?
>
> [탐색 결과]
> - Time.timeScale 제어: {건수}건
> - Coroutine 타이머(WaitForSeconds 등): {파일 목록}
> - Realtime 계열: {건수}건 (timeScale 무관)"
>
> - 멈춰야 함 → PORTING_VOCAB 광고 행 비고에 `게임중지: 필요` 갱신. Coroutine 타이머 파일 목록을 toss-porter 점검 대상으로 VOCAB에 추가.
> - 멈추지 않아도 됨 → `게임중지: 불필요` 갱신.

### (선택) 기획 문서 생성 — 포팅 파이프라인과 독립

`Docs/design/`의 IAP·IAA·저장-로드 기획 문서는 사업팀·기획팀이 읽는 문서로, 코드 변경(포팅) 파이프라인과 성격이 다르다. h5-port 메인 시퀀스에 포함하지 않는다 — 필요할 때 사용자가 개별 호출한다:
- `iap-analyzer`: IAP 분석 → `Docs/design/IAP.md`
- `iaa-analyzer`: IAA 분석 → `Docs/design/IAA.md`
- `save-point-analyzer`: 저장 시스템 분석 → `Docs/design/데이터-저장-로드.md`

세 에이전트 모두 2-A의 NATIVE_BASELINE.md·PORTING_VOCAB.md를 재활용하므로 2-A 이후 아무 시점에 실행 가능하다.

### 2-D. 포팅 전 준비 체크리스트 보고 [2-B-commit 완료 후]

아래 명령으로 브랜치 현황을 확인한 뒤, STEP 0~2에서 확인된 사실을 기반으로 보고를 출력한다.

```bash
git branch --show-current
```

```
포팅 전 준비 체크리스트

범례: ✅ 완료 | 👤 직접 처리 필요 | ⚠️ 주의 필요 | ⏭️ 스킵

────────────────────────────────────────────────────────
카테고리       항목                              결과
────────────────────────────────────────────────────────
프로젝트 준비  Trello 카드 등록                  👤 직접 처리 필요

프로젝트 준비  브랜치 나누기 ({플랫폼}/{버전})    ✅ {현재 브랜치명} / ⚠️ 브랜치 미분기
               근거: git branch 결과

프로젝트 준비  EUC-KR → UTF-8 디코딩            ✅ N개 변환 완료 / ✅ 이상 없음 / ⚠️ 미처리
               근거: STEP 1 결과

프로젝트 준비  HyperLane SDK 추가                ✅ Assets/HyperLane/ 확인 / ⚠️ 미설치
               근거: STEP 1-C 결과

환경 검증      Android 플랫폼 컴파일 확인         ✅ 이상 없음 / ⚠️ N건 오류 (처리됨/미처리)
               근거: STEP 1-A 결과

프로젝트 분석  정상 작동 테스트                   👤 직접 확인 필요 (크래시·오류 없는지)

프로젝트 분석  빌드 씬 확인                       ✅ N개 씬 확인 / ⚠️ 씬 누락 가능성
               근거: NATIVE_BASELINE.md 빌드 씬 목록

프로젝트 분석  자체 빌드 스크립트 및 H5Builder     ✅ BuildPlayer 없음 / ✅ H5Builder 반영
               근거: porting-scan BuildPlayer 탐색 결과

프로젝트 분석  게임 진입점 분석                   ✅ {GAME_INIT_METHOD} 확인
               근거: PORTING_VOCAB.md 게임 진입점 행

프로젝트 분석  Addressable 로드 시점 분석         ✅ 사용 중 ({ASSET_COUNTS}) / ⏭️ 미사용
               근거: PORTING_VOCAB.md {ASSET_COUNTS} 행
────────────────────────────────────────────────────────

👤 직접 처리 항목 완료 후 STEP 3(포터 선택)으로 진행하세요.
```

---

## STEP 2-E — 포터 실행 전 WebGL 컴파일 체크

포터 실행 직전에 WebGL 컴파일 상태를 확인한다. 포팅 대상 플랫폼(TOSS / PUREWEB)에 맞춰 실행.

```bash
# TOSS 또는 PUREWEB — 포팅 대상 플랫폼 선택
bash ~/github/h5-porting-workflow/templates/scripts/compile-check.sh TOSS
```

사전 점검(버전·설치·이 프로젝트 에디터 열림)은 스크립트에 내장되어 있다.
`⛔ STOP`이면 출력된 안내대로 조치될 때까지 대기하고, `✅`/`❌`면 아래 결과 처리로 진행한다.

**결과 처리**:

- 에러 0건 → "✅ WebGL 컴파일 정상" — STEP 3으로 진행
- 에러 있음 → 아래 순서로 처리한다. **오케스트레이터가 .cs·.meta 등 코드 파일을 직접 수정하지 않는다. 코드 수정은 포터 에이전트가 담당한다.**
  1. 에러 목록을 분류해 사용자에게 출력한다
  2. pureweb-checklist.md `## 이슈`에 기록한다:
     - porting-scan에서 "확인 필요"였던 항목은 실제 결과로 업데이트
     - 모든 오류를 `- [ ] {파일}:{라인} — [컴파일] {오류} — 포터에서 처리` 형식으로 추가
  3. pureweb-checklist.md를 커밋한다 (`[문서] WebGL 컴파일 체크 결과 기록`)
  4. AskUserQuestion으로 포터 에이전트 실행을 확인한다:
     > "WebGL 컴파일 오류 N건이 있습니다. 내용을 pureweb-checklist.md `## 이슈`에 기록했습니다.
     > 포터 에이전트가 D처리(DLL 비활성화)·A처리(가드 추가)로 해결합니다.
     > 에이전트를 실행할까요?"
     > - 예 → STEP 3으로 진행
     > - 아니오 → 종료

---

## STEP 3 — 포터 선택 및 실행

> **중요**: 포터는 반드시 `Agent 도구`의 `subagent_type` 파라미터로 실행한다.
> 포터 파일을 직접 읽고 오케스트레이터가 내용을 실행하지 않는다.
> - 퓨어웹: `Agent 도구, subagent_type: "pureweb-porter"`
> - 토스: `Agent 도구, subagent_type: "toss-porter"`

인자에 `toss` 또는 `pureweb`이 포함된 경우 AskUserQuestion 없이 해당 포터를 바로 실행한다.
인자가 없으면 AskUserQuestion으로 확인한다:

> "어떤 플랫폼으로 포팅하시겠어요?"
> - 퓨어웹 → Agent 도구로 `subagent_type: "pureweb-porter"` 실행
> - 토스 → Agent 도구로 `subagent_type: "toss-porter"` 실행
> - 둘 다 → 퓨어웹 먼저 완료 후 토스 순서로 실행
> - 나중에 → 안내 메시지 출력 후 종료

### STEP 3-A. 사람 준비 항목 확인 (토스 포팅인 경우만)

포터는 서브에이전트라 실행 중 사용자에게 물어볼 수 없다 — 사람이 준비해야 하는 항목을 포터 실행 전에 여기서 수집한다. 퓨어웹 포팅이면 이 단계를 건너뛴다(사람 준비 항목 없음).

`PORTING_VOCAB.md` `## Toss 전용` 섹션을 읽어 실제로 필요한 항목만 추린다:

| 항목 | 노출 조건 (VOCAB `## Toss 전용` 기준) |
|---|---|
| 배너 광고 위치 — 상단/하단 | 배너 행이 "없음"이 아님 |
| IAP PID 매핑 — 기존 PID ↔ Toss 상품 description | IAP 사용 (`{IAP_METHOD}` 행 있음) |
| 햅틱 타입 — 이벤트별 기획 명세 | 햅틱 행이 "없음" (역기획 필요한 경우) |
| 공유하기 문구 — 화면별 문구 | 공유하기 행이 "없음"이 아님 |
| 프로모션 ID — Toss 콘솔 등록 여부 | 프로모션 행이 "없음"이 아님 |
| 랭킹 버튼 추가 위치 | 랭킹 행이 "없음"이 아니고 기존 버튼이 없는 경우 |

추린 항목을 AskUserQuestion으로 한 번에 확인한다. **모든 항목에 "미확정" 선택지를 포함한다** — 기획이 확정되지 않았어도 포팅은 막히지 않는다(미확정 항목은 포터가 폴백 적용 또는 스킵+체크리스트 기록으로 처리).

답변(미확정 포함)은 STEP 3-B에서 생성하는 포팅 이슈 `## 사람 준비 항목`에 기록한다.

### STEP 3-B. 포팅 이슈 생성 (게임 repo에 gh remote 있는 경우만)

```bash
gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null && echo "REPO_OK" || echo "NO_REMOTE"
```

- `NO_REMOTE` → 이슈 생성 생략, STEP 3-C(포터 실행)로 바로 진행 (STEP 3-A 답변은 포터 prompt에 실어 보낼 수 없으므로 체크리스트 `## 확인 필요`에 기록해 포터가 읽게 한다).
- `REPO_OK` → 아래 형식으로 이 게임 repo에 포팅 이슈를 생성한다:

```bash
BODY_FILE="$(mktemp)"
cat > "$BODY_FILE" <<'EOF'
## 진행 상황
정본: 기반(컴파일/런타임/공백) 이슈는 항상 `Docs/porting/pureweb-checklist.md`, 플랫폼 전용 이슈는 `Docs/porting/{PLATFORM}-checklist.md` (이 이슈는 진행 미러 — 상세 상태는 두 정본 파일 참조)

{체크리스트 단계 표 스냅샷}

## 사람 준비 항목 (토스 포팅만 — STEP 3-A 답변)
확정된 항목은 `[x]` + 확정값 기재, 미확정이면 `[ ]`로 남긴다. 해당 없는 항목은 줄을 지운다.
- [ ] 배너 위치 (상단/하단):
- [ ] IAP PID 매핑:
- [ ] 햅틱 타입:
- [ ] 공유하기 문구:
- [ ] 프로모션 ID:
- [ ] 랭킹 버튼 위치:

## 확인 필요 / 미확정
(포터 실행 중 항목이 추가되면 여기 기록됨)
EOF

gh issue create \
  --title "[포팅] {PLATFORM} — {프로젝트명}" \
  --body-file "$BODY_FILE"

rm -f "$BODY_FILE"
```

생성된 이슈 번호를 기억해 STEP 3-C의 포터 prompt에 전달한다.

### STEP 3-C. 포터 실행

포터를 실행하기 직전, 포팅 이슈 `## 사람 준비 항목`에 미체크(`[ ]`) 항목이 남아 있으면 AskUserQuestion으로 한 번 재확인한다 — "그 사이 확정된 항목이 있나요?" (질문 수집과 포터 실행 사이에 기획이 확정됐을 수 있다). 확정으로 바뀐 항목은 `[x]` + 값으로 이슈 본문을 갱신한 뒤 진행한다.

포터 실행 시 Agent 도구의 `prompt`에는 **현재 상태 컨텍스트만** 전달한다. 태스크 목록·처리 순서·수정 방법을 직접 기술하지 않는다. 포터의 파이프라인은 에이전트 자체 지침을 따른다.

**prompt에 포함할 내용 (이것만)**:
```
--orchestrated

프로젝트 경로: {worktree 절대경로 또는 현재 경로}
브랜치: {현재 브랜치명}
이미 완료된 작업: {STEP 2-E에서 커밋된 내용 요약 — 없으면 "없음"}
포팅 이슈: #{STEP 3-B에서 생성한 이슈 번호 — 없으면 "없음"}
```

**후속 모드(부분 수정)로 재호출하는 경우** 아래 블록을 추가한다 — 포터는 이 항목들과 연결된 TODO/스킵 지점만 수정하고 전체 재작업은 하지 않는다:
```
부분 수정 모드: 아래 확정 항목만 반영, 전체 재작업 금지
{확정된 항목 목록 — 항목명: 확정값}
```

**prompt에 포함하지 않을 것**: 구체적 파일명, 라인 번호, 처리 순서, 태스크 목록. 에이전트가 NATIVE_BASELINE.md·pureweb-checklist.md·PORTING_VOCAB.md를 읽고 스스로 판단한다.

**포터 완료 후 즉시 STEP 4로 진행한다** — 포터의 완료 리포트를 출력한 뒤 사용자 확인을 기다리거나 별도 명령을 요구하지 않는다.

```
# 나중에 선택 시 출력
STEP 1~2 완료. 포터는 준비되면 아래 명령으로 실행하세요:
- 퓨어웹: /pureweb-porter
- 토스:   /toss-porter
```

---

## STEP 4 — 포팅 검증

STEP 3 포터 완료 후 h5-port-verify.py로 플랫폼별 처리 누락을 최종 검증한다.

`{SCRIPTS_PATH}`는 NATIVE_BASELINE.md 헤더의 `스크립트 경로:` 값에서 확인해 `--scripts` 인자로 전달한다:

```bash
head -5 Docs/porting/NATIVE_BASELINE.md
```

```bash
# 퓨어웹 포팅인 경우
python3 ~/github/h5-porting-workflow/templates/scripts/h5-port-verify.py \
  --platform WEBGL_PUREWEB \
  --vocab Docs/porting/PORTING_VOCAB.md \
  --scripts {SCRIPTS_PATH}

# 토스 포팅인 경우
python3 ~/github/h5-porting-workflow/templates/scripts/h5-port-verify.py \
  --platform WEBGL_TOSS \
  --vocab Docs/porting/PORTING_VOCAB.md \
  --scripts {SCRIPTS_PATH}
```

| 결과 | 대응 |
|---|---|
| `✅ 이상 없음` | 포팅 완료 |
| `❌ 미처리` | 해당 파일 수정 후 재실행 |
| `⚠️ 확인 필요` | 포터 에이전트 검증 섹션의 verify-exceptions 절차 참조 |

### STEP 4-A. 포팅 이슈 종료 처리

STEP 3-B에서 이슈를 생성했으면(없으면 이 단계 생략). 후속 모드(부분 수정 재호출)에서도 동일하게 적용한다:

- 검증 `✅ 이상 없음` **+** 이슈 본문 `## 확인 필요 / 미확정`에 남은 항목 없음 → `gh issue close`로 검증 결과 코멘트와 함께 종료.
- 위 조건을 만족하지 않으면(미확정 항목 남음 등) 이슈를 **open으로 유지**하고 남은 항목을 코멘트로 남긴다.

체크리스트가 작업 진행의 정본이고, 이 이슈는 진행 상황을 비추는 미러다 — 기반(컴파일/런타임/공백) 이슈는 `pureweb-checklist.md`, 플랫폼 전용 이슈는 `Docs/porting/{platform}-checklist.md`가 각각 정본이다. 상태가 어긋나면 체크리스트를 기준으로 이슈를 갱신한다.
