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

## STEP 0 — 프로젝트 초기 설정

`~/.claude/commands/project/porting-init.md` 파일을 읽고 해당 지침에 따라 실행한다.

완료 후 아래 절차를 순서대로 실행한다.

### 0-A. 브랜치 확인

```bash
git branch --show-current
```

브랜치명이 `플랫폼/버전` 형식(예: `toss/v1.0`, `pureweb/1.2.3`)인지 확인한다.

- 형식이 맞으면 → 0-B로 진행
- 형식이 맞지 않으면(예: `main`, `master`, 빈 값) → 아래 메시지를 출력하고 **사용자가 확인할 때까지 대기**:

```
⚠️ 현재 브랜치: {브랜치명}

포팅 커밋 전에 작업 브랜치(플랫폼/버전 형식)로 전환해 주세요.
전환 완료 후 계속 진행하겠습니까?
```

AskUserQuestion으로 확인 후 진행한다.

### 0-B. Addressables 패키지 확인

`HLAddressableTool.cs`는 Addressables 패키지가 없으면 컴파일 오류가 난다. 패키지 설치 여부를 확인한다.

```bash
grep -q "com.unity.addressables" Packages/manifest.json \
  && echo "ADDRESSABLES_OK" \
  || echo "ADDRESSABLES_MISSING"
```

- `ADDRESSABLES_OK` → 0-C로 진행
- `ADDRESSABLES_MISSING` → AskUserQuestion으로 확인:

> "`HLAddressableTool.cs`는 Addressables 패키지가 필요하지만 현재 미설치 상태입니다.
> - 패키지 설치 후 계속 → Unity Editor에서 `com.unity.addressables`를 설치한 뒤 알려주세요.
> - 커밋에서 제외하고 계속 → `HLAddressableTool.cs`를 제외하고 나머지만 커밋합니다."

제외 선택 시: 0-C의 `git add` 목록에서 `HLAddressableTool.cs`와 해당 `.meta`를 빼고 진행한다.

### 0-C. STEP 0 산출물 커밋

STEP 0에서 생성·수정된 파일을 커밋한다.

```bash
git add CLAUDE.md Docs/README.md Docs/FRAMEWORK_REFERENCE.md \
        Assets/Editor/CompileChecker.cs Assets/Editor/CompileChecker.cs.meta \
        Assets/Editor/CompileResultWindow.cs Assets/Editor/CompileResultWindow.cs.meta \
        Assets/Editor/TextureFormatSetter.cs Assets/Editor/TextureFormatSetter.cs.meta \
        Assets/Editor/HLAddressableTool.cs Assets/Editor/HLAddressableTool.cs.meta
git status --short
```

`.meta` 파일이 없는 항목은 `--ignore-unmatch`로 넘어간다. `git status`로 스테이징 목록을 확인한 뒤 커밋한다:

```bash
git commit -m "[문서] 포팅 초기 설정 — CLAUDE.md·FRAMEWORK_REFERENCE.md·Editor 툴 추가"
```

커밋 성공 후 STEP 1로 진행한다.

---

## VOCAB 변수 매핑 컨벤션

porting-scan, toss-porter, pureweb-porter 등 모든 h5 에이전트는 아래 변수명을 공유한다.
PORTING_VOCAB.md를 읽은 뒤 해당 행의 메서드/클래스명으로 플레이스홀더를 대체한다.

| 플레이스홀더 | PORTING_VOCAB.md 행 | 예시 |
|---|---|---|
| `{LOAD_METHOD}` | 불러오기 | `LoadCloud()` |
| `{SAVE_METHOD}` | 저장 | `SaveCloud()` |
| `{SOUND_CLASS}` | 사운드 | `SoundManager` |
| `{AD_REWARDED_METHOD}` | 광고 (보상형) | `ShowRewardedAd()` |
| `{AD_INTERSTITIAL_METHOD}` | 광고 (전면) | `ShowInterstitialAd()` |
| `{IAP_METHOD}` | IAP | `InappPurchase()` |
| `{GAME_INIT_METHOD}` | 게임 진입점 | `InitGame()` |
| `{PRICE_UI_CLASS}` | 가격 표시 UI (Toss 전용) | `UIShopPrice` |
| `{BANNER_FILE}` | 배너 광고 (Toss 전용) | `AdManager.cs` |
| `{HAPTIC_FILE}` | 햅틱/진동 (Toss 전용) | `HapticManager.cs` |
| `{RANKING_FILE}` | 랭킹 연동 (Toss 전용) | `RankManager.cs` |
| `{SHARE_FILE}` | 공유하기 (Toss 전용) | `ShareManager.cs` |
| `{PROMOTION_TYPE}` | 프로모션 방식 (Toss 전용) | `Managed` |
| `{SAFEAREA_CLASS}` | SafeArea 처리 클래스 (Toss 전용) | `SafeAreaAdjuster` |
| `{UID_VERSION_FILE}` | UID/version 표시 UI 클래스 (Toss 전용) | `DebugInfoUI` |
| `{REMOVE_UI_LIST}` | 불필요 UI 후보 파일:라인 목록 (Toss 전용) | `UIShop.cs:42, UIMenu.cs:88` |
| `{LOCALIZATION_FILE}` | 로컬라이제이션 클래스 (Toss 전용) | `LocalizationManager.cs` |
| `{ASSET_COUNTS}` | 에셋 현황 (오디오·텍스쳐 수·Addressables) | `오디오: 30개 / 텍스쳐: 800개 / Addressables: 사용중` |
| `{SCRIPTS_PATH}` | — | porting-scan 사전 감지로 확정 |

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
  || echo "✗ 변환 실패: {파일경로}"
```

---

## STEP 1-A — Android 플랫폼 컴파일 확인

포팅 전 Android 빌드 타겟 기준으로 컴파일이 정상인지 확인한다.
**오류가 있으면 사용자 결정 없이 STEP 1-B로 넘어가지 않는다.**

```bash
UNITY_VERSION=$(grep "m_EditorVersion:" ProjectSettings/ProjectVersion.txt | awk '{print $2}')
UNITY_BIN="/Applications/Unity/Hub/Editor/${UNITY_VERSION}/Unity.app/Contents/MacOS/Unity"
LOG_FILE="/tmp/unity_android_compile.log"

${UNITY_BIN} \
  -batchmode -quit \
  -projectPath "$(pwd)" \
  -buildTarget Android \
  -logFile "${LOG_FILE}" \
  || true

grep -E "error CS|^error " "${LOG_FILE}"
```

오류가 없으면 "✅ Android 컴파일 정상" 출력 후 STEP 1-B로 진행한다.

오류가 있으면 아래 기준으로 분류해서 사용자에게 보고한다:

**분류 기준**

| 분류 | 판단 조건 |
|---|---|
| 파일 누락 | `error CS0246` / `CS0234` — 타입·네임스페이스를 찾지 못함. 스크립트 파일 자체가 없거나 경로 불일치 |
| SDK 문제 | `Assets/Plugins`, `Assets/Firebase`, `Assets/GoogleMobileAds` 등 외부 SDK 경로에서 발생하는 오류, 또는 알 수 없는 DLL 참조 |
| 기타 컴파일 오류 | 위에 해당하지 않는 문법 오류, 메서드 누락 등 |

보고 형식:

```
⚠️ Android 컴파일 오류 발견

[파일 누락 (N건)]
- Assets/Scripts/Foo.cs:12 — error CS0246: 'BarClass' not found
...

[SDK 문제 (N건)]
- Assets/Plugins/Firebase/... — error CS0234: ...
...

[기타 (N건)]
- ...
```

각 분류별로 AskUserQuestion으로 처리 방안을 확인한다:

- **파일 누락**: "누락된 파일을 추가하시겠습니까, 아니면 해당 참조를 제거·주석 처리하시겠습니까?"
- **SDK 문제**: "SDK를 재설치하시겠습니까, 아니면 해당 SDK를 포팅 범위에서 제외하고 진행하시겠습니까?"
- **기타**: "직접 수정하시겠습니까, 아니면 unity-compile-checker 에이전트를 실행할까요?"

사용자가 수정을 선택하면 조치 완료 후 컴파일을 재실행해 오류가 사라졌는지 확인한다.
모든 분류에서 처리가 완료(수정 또는 의도적 제외 결정)된 후 STEP 1-B로 진행한다.

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
> - 설치하겠습니다 → Unity Editor에서 HyperLane 패키지를 임포트한 뒤 완료되면 알려달라고 안내. 확인 후 STEP 2로.
> - 설치 없이 진행 → 이후 분석 및 포팅에서 HLSDK 연동 불가 상태로 진행. PORTING_ANALYSIS.md에 "⚠️ HyperLane 미설치" 기록.

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
git add Docs/porting/PORTING_VOCAB.md Docs/porting/PORTING_ANALYSIS.md
git status --short
```

스테이징 확인 후 커밋한다:

```bash
git commit -m "[문서] 포팅 분석 완료 — PORTING_VOCAB·PORTING_ANALYSIS 생성"
```

### 2-C. 기획 문서 생성 [2-B-commit 완료 후 — Agent 병렬 실행]

PORTING_VOCAB.md가 2-A에서 생성·검증됐으므로 세 에이전트 모두 SCRIPTS_PATH·매니저 파일명을 재활용한다.

같은 응답에서 세 에이전트를 Agent 도구로 동시 호출한다:
- `iap-analyzer`: IAP 분석 → `Docs/design/IAP.md` 저장
- `iaa-analyzer`: IAA 분석 → `Docs/design/IAA.md` 저장
- `save-point-analyzer`: 저장 시스템 분석 → `Docs/design/데이터-저장-로드.md` 저장

**[2-C 완료 후] 광고 중 게임 중지 확인**

PORTING_VOCAB에 `게임중지: 확인 필요`로 기록된 항목이 있으면 AskUserQuestion으로 확인한다.
IAA.md 분석 결과(광고 종류·Placement 수)와 PORTING_VOCAB의 탐색 결과(TimeScale·Coroutine 파일 목록)를 함께 보여준다:

> "광고(전면/보상형)가 표시되는 동안 게임을 일시 정지해야 하나요?
>
> [IAA 분석 결과] 광고 종류: {보상형·전면 등}, Placement 수: N개
> [탐색 결과]
> - Time.timeScale 제어: {건수}건
> - Coroutine 타이머(WaitForSeconds 등): {파일 목록}
> - Realtime 계열: {건수}건 (timeScale 무관)"
>
> - 멈춰야 함 → PORTING_VOCAB 광고 행 비고에 `게임중지: 필요` 갱신. Coroutine 타이머 파일 목록을 toss-porter 점검 대상으로 VOCAB에 추가.
> - 멈추지 않아도 됨 → `게임중지: 불필요` 갱신.

### 2-C-commit. 기획 문서 커밋 [2-C 완료 후]

2-C에서 생성된 기획 문서를 커밋한다.

```bash
git add Docs/design/IAP.md Docs/design/IAA.md "Docs/design/데이터-저장-로드.md"
git status --short
```

스테이징 확인 후 커밋한다:

```bash
git commit -m "[문서] 기획 문서 생성 — IAP·IAA·저장-로드 분석"
```

### 2-D. 포팅 전 준비 체크리스트 보고 [2-A~2-C-commit 완료 후]

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
               근거: PORTING_ANALYSIS.md 빌드 씬 목록

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
pgrep -x Unity && echo "UNITY_OPEN" || echo "UNITY_CLOSED"
```

- `UNITY_OPEN` → "⚠️ Unity가 열려 있어 batchmode 실행 불가. Unity를 닫은 뒤 진행하거나, Tools/H5/Compile Check 메뉴를 직접 실행하고 결과를 알려주세요." 출력 후 대기.
- `UNITY_CLOSED` → 아래 명령 실행:

```bash
UNITY_VERSION=$(grep "m_EditorVersion:" ProjectSettings/ProjectVersion.txt | awk '{print $2}')
UNITY_BIN="/Applications/Unity/Hub/Editor/${UNITY_VERSION}/Unity.app/Contents/MacOS/Unity"

# TOSS 또는 PUREWEB — 포팅 대상 플랫폼 선택
"${UNITY_BIN}" -batchmode -quit \
  -projectPath "$(pwd)" \
  -buildTarget WebGL \
  -executeMethod CompileChecker.Run \
  -customArgs TOSS \
  -logFile Docs/porting/compile_result.log 2>/dev/null

grep -E "error CS" Docs/porting/compile_result.log | sort -u
```

**결과 처리**:

- 에러 0건 → "✅ WebGL 컴파일 정상" — STEP 3으로 진행
- 에러 있음 → 아래 순서로 처리한다. **오케스트레이터가 .cs·.meta 등 코드 파일을 직접 수정하지 않는다. 코드 수정은 포터 에이전트가 담당한다.**
  1. 에러 목록을 분류해 사용자에게 출력한다
  2. PORTING_ANALYSIS.md 컴파일 이슈 테이블에 기록한다:
     - porting-scan에서 "확인 필요"였던 항목은 실제 결과로 업데이트
     - 모든 오류에 "⬜ 포터에서 처리" 상태 표시
  3. PORTING_ANALYSIS.md를 커밋한다 (`[문서] WebGL 컴파일 체크 결과 기록`)
  4. AskUserQuestion으로 포터 에이전트 실행을 확인한다:
     > "WebGL 컴파일 오류 N건이 있습니다. 내용을 PORTING_ANALYSIS.md에 기록했습니다.
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

포터 실행 시 Agent 도구의 `prompt`에는 **현재 상태 컨텍스트만** 전달한다. 태스크 목록·처리 순서·수정 방법을 직접 기술하지 않는다. 포터의 파이프라인은 에이전트 자체 지침을 따른다.

**prompt에 포함할 내용 (이것만)**:
```
--orchestrated

프로젝트 경로: {worktree 절대경로 또는 현재 경로}
브랜치: {현재 브랜치명}
이미 완료된 작업: {STEP 2-E에서 커밋된 내용 요약 — 없으면 "없음"}
```

**prompt에 포함하지 않을 것**: 구체적 파일명, 라인 번호, 처리 순서, 태스크 목록. 에이전트가 PORTING_ANALYSIS.md를 읽고 스스로 판단한다.

```
# 나중에 선택 시 출력
STEP 1~2 완료. 포터는 준비되면 아래 명령으로 실행하세요:
- 퓨어웹: /pureweb-porter
- 토스:   /toss-porter
```

---

## STEP 4 — 포팅 검증

STEP 3 포터 완료 후 h5-port-verify.py로 플랫폼별 처리 누락을 최종 검증한다.

PORTING_VOCAB.md에서 `{SCRIPTS_PATH}`를 확인해 `--scripts` 인자로 전달한다.

```bash
# 퓨어웹 포팅인 경우
python3 ~/github/.templates/scripts/h5-port-verify.py \
  --platform WEBGL_PUREWEB \
  --vocab Docs/porting/PORTING_VOCAB.md \
  --scripts {SCRIPTS_PATH}

# 토스 포팅인 경우
python3 ~/github/.templates/scripts/h5-port-verify.py \
  --platform WEBGL_TOSS \
  --vocab Docs/porting/PORTING_VOCAB.md \
  --scripts {SCRIPTS_PATH}
```

| 결과 | 대응 |
|---|---|
| `✅ 이상 없음` | 포팅 완료 |
| `❌ 미처리` | 해당 파일 수정 후 재실행 |
| `⚠️ 확인 필요` | 포터 에이전트 검증 섹션의 verify-exceptions 절차 참조 |
