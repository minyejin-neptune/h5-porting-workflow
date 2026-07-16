---
description: 포팅 사전 분석 스캔 — SDK·런타임·게임구조를 분석해 NATIVE_BASELINE.md·PORTING_VOCAB.md·체크리스트 2종 생성
---

# 포팅 사전 분석 스캔

프로젝트를 **코드 수정 없이** 분석해 `Docs/porting/` 아래 4파일을 생성한다:
- `NATIVE_BASELINE.md` — 포팅 전 네이티브 불변 스냅샷 (프로젝트 정보·외부 SDK 목록·게임 구조)
- `PORTING_VOCAB.md` — 위치 사전 (기능→파일:라인)
- `pureweb-checklist.md` — 기반 작업목록 (퓨어웹 포팅 작업이 소비 — 컴파일/런타임/공백 이슈·확인 필요)
- `toss-checklist.md` — 플랫폼 작업목록 (플랫폼 포팅 작업이 소비 — toss 전용 이슈 + 광고·IAP 실동작 확인 필요)

> 📚 HyperLane SDK 매뉴얼: https://github.com/neptunez-dev/hyperlane-sdk/tree/main/docs/manual

`$ARGUMENTS`로 포팅 플랫폼을 지정할 수 있다 (`toss` / `pureweb`). 지정하지 않으면 사전 감지 후 AskUserQuestion으로 확인한다.

추론 금지. 코드에서 확인한 사실만 기재. 확인 불가 시 "확인 필요" 표시.
출처는 파일명:라인번호 형식으로 명시.

---

## 사전 감지

**구버전 문서 감지 (시점 분리 마이그레이션)**

```bash
ls Docs/porting/NATIVE_BASELINE.md 2>/dev/null && echo "BASELINE: EXISTS"
ls Docs/porting/PORTING_ANALYSIS.md 2>/dev/null && echo "OLD_ANALYSIS: EXISTS"
```

- `BASELINE: EXISTS` → 신 구조 — 그대로 진행
- 둘 다 없음 → 신규 프로젝트 — 그대로 진행
- BASELINE 없고 `OLD_ANALYSIS: EXISTS`만 → 시점 분리 이전 프로젝트. AskUserQuestion으로 이관을 제안한다:
  > "구 형식 문서(PORTING_ANALYSIS.md)가 있습니다. 새 구조(NATIVE_BASELINE + 체크리스트)로 이관할까요?"
  > - 이관 — 파일을 `NATIVE_BASELINE.md`로 개명하고, 가변 섹션(컴파일·런타임·공백 이슈, 확인 필요, 빌드 기록, 처리 현황류)을 체크리스트로 이동한다. 기존 상태·커밋 해시는 보존.
  > - 유지 — 이관하지 않고 스캔을 중단한다 (구 구조 그대로 사용)

**항목 자동 파악** — 아래 항목을 자동 파악한다. 파악 불가 시 사용자에게 질문.

```bash
# SCRIPTS_PATH
find Assets -maxdepth 3 -type d -name "Scripts" 2>/dev/null

# VOCAB_FILE 존재 여부
ls Docs/porting/PORTING_VOCAB.md 2>/dev/null && echo "EXISTS" || echo "NONE"

# SDK 폴더 목록 (dll/aar/framework 포함 폴더 = 외부 SDK)
find Assets -maxdepth 3 \( -name "*.dll" -o -name "*.aar" -o -name "*.framework" \) 2>/dev/null \
  | sed 's|/[^/]*$||' | sort -u

# EXTRA_PATHS — .cs 깊이 분포 (SDK 폴더 목록 감지 직후 실행, 판단 기준은 아래 블록 참고)
find Assets -name "*.cs" 2>/dev/null | awk -F/ '{print NF-1}' | sort -n | uniq -c

# jslib 파일 목록
find Assets -name "*.jslib" 2>/dev/null

# Unity 버전
grep "m_EditorVersion:" ProjectSettings/ProjectVersion.txt 2>/dev/null | awk '{print $2}'

# HyperLane 설치 여부
ls Assets/HyperLane/ 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"

# Build Settings 등록 씬 목록 + 파일 누락 여부
python3 -c "
import re, os
content = open('ProjectSettings/EditorBuildSettings.asset').read()
scenes = re.findall(r'enabled: (\d)\s+path: (.+)', content)
for enabled, path in scenes:
    path = path.strip()
    status = 'ON ' if enabled == '1' else 'OFF'
    exists = '✓' if os.path.exists(path) else '❌ 파일 없음'
    print(f'[{status}] {exists}  {path}')
" 2>/dev/null || echo "EditorBuildSettings.asset 없음 — find로 대체"
find Assets/Scenes -name "*.unity" 2>/dev/null | head -20

# 자체 빌드 스크립트
grep -rln "BuildPlayer\|BuildPipeline" Assets --include="*.cs" 2>/dev/null | grep -v HyperLane
```

> **EXTRA_PATHS 판단**: `.cs` 깊이 분포에서 최다빈도 깊이(mode)를 기준으로 잡는다. mode보다 **3단계 이상 깊은** 깊이에 파일이 있으면 이상치 후보(단일 벤더 폴더·자동생성 코드 가능성 — SDK 폴더 감지(위 46행)·Scripts 탐지(위 40행)와 동일한 `3` 기준 사용) — 실제 경로를 확인한다:
> ```bash
> find Assets -name "*.cs" 2>/dev/null | awk -F/ -v min={mode+3} 'NF-1 >= min {print}'
> ```
> - 이상치 경로가 SDK 폴더 목록(위 46행 감지 결과)과 겹치면 **자동 제외** → SCAN_DEPTH = mode+2.
> - 안 겹치면 EXTRA_PATHS 포함 여부를 사용자에게 확인 → 승인 시 SCAN_DEPTH = 실측 최대 깊이, 미승인·미확인 시 안전하게 SCAN_DEPTH = mode+2.
> - 이상치가 처음부터 없으면(전부 mode+2 이내) 확인 없이 SCAN_DEPTH = 실측 최대 깊이.
>
> SCAN_DEPTH가 정해지면 EXTRA_PATHS 최종 목록을 만든다. **SCRIPTS_PATH(위 40행 감지 결과) 자신과 그 하위 전체를 제외**한다 — 이름 패턴(`/Scripts$`)만으로는 `Scripts/UI` 같은 하위 폴더가 걸러지지 않아 SCRIPTS_PATH와 중복 스캔되므로, 감지된 실제 경로로 제외 패턴을 만든다:
> ```bash
> SCRIPTS_PATH_PATTERN=$(find Assets -maxdepth 3 -type d -name "Scripts" 2>/dev/null | awk '{printf "^%s(/|$)|", $0}' | sed 's/|$//')
> find Assets -maxdepth {SCAN_DEPTH} -name "*.cs" 2>/dev/null \
>   | sed 's|/[^/]*$||' | sort -u \
>   | grep -vE "HyperLane" \
>   | grep -vE "$SCRIPTS_PATH_PATTERN"
> # → 위 결과에서 SDK 폴더 목록과 겹치는 경로 추가 제외
> # → SCAN_PATHS = SCRIPTS_PATH + EXTRA_PATHS (비어 있으면 SCRIPTS_PATH만)
> ```

> **탐색 경로 원칙**: STEP 2·3·4 grep은 `{SCAN_PATHS}`(= SCRIPTS_PATH + EXTRA_PATHS)를 사용한다.
> STEP 1 SDK 영향 파일 수 카운트만 `{SCRIPTS_PATH}` 단독 사용 (SDK 자체 코드 오염 방지).
> EXTRA_PATHS가 없으면 SCAN_PATHS = SCRIPTS_PATH.

감지 결과를 사용자에게 보여주고 확인받은 뒤 분석을 시작한다.

## 플랫폼 선택

`$ARGUMENTS`가 지정된 경우 → 해당 값을 플랫폼으로 사용하고 바로 진행.

지정되지 않은 경우 → AskUserQuestion:

> "어떤 플랫폼으로 포팅하나요? Toss는 플랫폼 전용 스캔 구간(4-I)이 반영됩니다. PureWeb은 WebGL 공통 스캔만으로 충분합니다(PureWeb 고유 스캔 항목 없음 — pureweb-porter가 H5Builder 설정 등을 자체 확인)."
> - Toss — 4-I 실행
> - PureWeb — 공통 스캔만 진행 (4-I 스킵)
> - 전체 — 4-I 포함 전체 실행

선택한 플랫폼을 이후 스캔 전체에 반영한다.

---

## 파이프라인

```
[사전 감지] SCRIPTS_PATH, SDK 폴더 목록 확정
      ↓
[플랫폼 선택] $ARGUMENTS 또는 AskUserQuestion (toss / pureweb / 전체)
      ↓
[병렬 실행] STEP 1 SDK 목록 확보(에이전트)  |  STEP 3 런타임 이슈  |  STEP 4 게임 구조 파악  |  STEP 6 WebGL 공백
      ↓ (STEP 1 완료 후)
[순차 실행] D → A 교차 검증  (D 대상 SDK의 코드 가드 누락 파일 확인)
      ↓
[순차 실행] STEP 2 컴파일 이슈  (SDK 네임스페이스 전체 가드 누락 확인)
      ↓
[순차 실행] STEP 5 문서 저장
```

STEP 1(Agent 호출)·3·4는 서로 독립적이므로 같은 응답에서 동시에 실행한다.
D → A 교차 검증은 STEP 1 수용 목록에서 D 대상 SDK가 확정된 후 즉시 실행한다.
STEP 2는 교차 검증 결과를 포함해 전체 컴파일 이슈를 최종 정리한다.

---

### STEP 1 — 외부 SDK 목록 확보 [병렬]

`Agent 도구(subagent_type: "sdk-list-analyzer")`를 실행한다. SDK 목록 작성 로직(감지·용도 판단·A/B/C/D 분류·Zero-Hit Fallback)은 이 에이전트가 **단일 소스**다 — 여기서 재구현하지 않는다.

에이전트가 스스로 판정하므로 조건 분기 없이 항상 호출한다 (에이전트 STEP 0):
- `NATIVE_BASELINE.md` 존재 → 분석 생략 안내 — BASELINE `## 외부 SDK 목록`을 사용한다 (재스캔 케이스)
- `Docs/porting/.sdk-list.md` 존재 + 신선(기준 커밋 대비 관련 변경 0건) → 재분석 생략, 기존 산출물 사용
- 그 외(낡음/없음) → 분석 실행

완료 후 `Docs/porting/.sdk-list.md`를 Read해 **spot-check**(표에서 1~2행의 폴더 실존을 `ls`로 확인) 후 수용한다. 이 목록이 이후 단계(D→A 교차 검증, STEP 5 NATIVE_BASELINE 기재)의 외부 SDK 목록이다.

처리 방법 A/B/C/D 정의는 sdk-list-analyzer 에이전트 문서를 따른다.

> **타이머/트위닝 라이브러리 메모**: 산출물 `## 메모`에 기록돼 있다 — 4-C 광고 중 게임 중지 탐색 시 외부 라이브러리 Unscaled 설정 grep과 함께 사용한다.

#### D → A 교차 검증 [STEP 1 완료 직후]

D로 분류된 SDK는 DLL이 WebGL 컴파일에서 제거되므로, 해당 DLL의 타입을 참조하는 **모든** C# 코드도 반드시 A(또는 B/C) 처리가 필요하다.
STEP 1에서 D 대상 SDK가 확정되면, 각 SDK의 네임스페이스로 즉시 교차 검증한다.

```bash
# D 대상 SDK별로 — UNITY_WEBGL 가드 없는 using 파일 전체 추출
grep -rln "using {D_SDK_네임스페이스}" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | xargs -I{} sh -c 'grep -l "UNITY_WEBGL" {} 2>/dev/null || echo "A_MISSING: {}"'
```

- `A_MISSING:` 로 출력된 파일 → A 처리 누락. pureweb-checklist.md `## 이슈`에 `[컴파일]` 항목으로 반드시 포함
- D 대상이지만 `using` 0건인 SDK (예: Parse) → 코드 가드 불필요, meta만 처리로 충분. "코드 사용 없음 — D만 적용" 으로 명시

#### 래퍼 호출부 역추적 [D→A 교차 검증 직후]

A 처리 완료 파일(`using D_SDK_NS` 있고 UNITY_WEBGL 가드 있는 파일)은 SDK를 래핑한다.
해당 래퍼 클래스의 public 메서드를 **외부에서 가드 없이 호출하는 파일**을 역추적한다.
`ServiceManager.Instance.ShowVideo()`, `_svc.ShowVideo()` 등 변수명·호출 패턴에 무관하게 탐지된다.

```bash
# 스크립트가 없으면 템플릿에서 복사
[ -f Docs/porting/h5-port-verify.py ] || cp $H5PW_ROOT/templates/scripts/h5-port-verify.py Docs/porting/

python3 Docs/porting/h5-port-verify.py \
  --platform {PLATFORM_SYMBOL} \
  --mode scan-callers \
  --wrapper {A처리파일1} \
  --wrapper {A처리파일2} \
  --scripts {SCRIPTS_PATH}
# EXTRA_PATHS가 있으면 --scripts 반복 추가
```

`{A처리파일}`: D→A 교차 검증에서 WEBGL 가드 있음으로 확인된 파일들.

출력 처리:

| 결과 | 처리 |
|---|---|
| `CALLER_MISSING` 건수 0 | 래퍼 호출부 이상 없음 |
| `CALLER_MISSING` 건수 1 이상 | pureweb-checklist.md `## 이슈`에 `[컴파일]` 항목으로 추가. 이슈: `CALLER_MISSING: {클래스}.{메서드}() 호출 — 가드 없음` / 처리방법: A |

**내부 미가드 SDK 호출 확인 (INTERNAL_UNGUARDED)**

위 역추적과 별개로, A 처리 완료 파일 **자신** 내부에서 SDK를 가드 없이 호출하는 메서드가 있는지 Read로 확인한다.

A 처리 파일을 Read한 후:
- `#if` WEBGL 가드 **바깥**에 있는 메서드(Init\*, Initialize\*, Start, Awake 포함)에서 SDK 직접 호출이 있으면
- → pureweb-checklist.md `## 이슈`에 `[컴파일]` 항목으로 추가. 이슈: `INTERNAL_UNGUARDED: {메서드명}() — 가드 없이 SDK 호출` / 처리방법: A

> grep 결과만으로 판정하지 않는다. 파일 Read 후 `#if` 블록 경계를 직접 확인한다.

> 전 SDK grep 0건이어도 sdk-list-analyzer가 Zero-Hit Fallback(의존성 메타데이터 탐색)을 수행한다 — 산출물에 `처리 방법: 확인 필요`, `상태: fallback 식별`로 표기되어 돌아온다.

---

### STEP 3 — 런타임 이슈 탐색 [병렬]

Unity 범용 패턴으로 탐색. SDK 목록과 무관하게 실행 가능.

```bash
# CORS: UnityWebRequest 직접 호출 (WEBGL 가드 없는 것)
grep -rn "UnityWebRequest\|new WWW\b" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v "#if\|//\|HyperLane"

# 파일 IO: WebGL 미지원
grep -rn "File\.\(Read\|Write\|Exists\|Delete\|Create\)\|StreamWriter\|StreamReader\|BinaryWriter\|BinaryReader" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v "#if\|//"

# persistentDataPath 직접 접근
grep -rn "Application\.persistentDataPath\|Application\.dataPath" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v "#if\|//"

# 전체화면 유발
grep -rn "Screen\.SetResolution" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null

# SafeArea SDK 의존 계산
grep -rln "SafeArea\|safeArea\|GetSafeArea" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null

# 멀티스레드 (WebGL 단일 스레드)
grep -rn "new Thread\b\|Task\.Run\b\|ThreadPool\." {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v "#if\|//"

# Application.OpenURL — WebGL에서 현재 탭 이탈 위험
grep -rn "Application\.OpenURL" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v "#if\|//"
```

**Zero-Hit Fallback** — 위 런타임 이슈 grep 7종이 모두 0건이면 namespace 의존성을 확인한다 (최대 5개 파일, 1단계):

```bash
grep -rln "using System\.IO\|using System\.Net\|using System\.Threading" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -5
```

히트 파일 상위 5개를 Read해 실제 API 호출(파일:라인)을 확인한다.
근거 있으면 pureweb-checklist.md `## 이슈`에 `[런타임]` 항목으로 `(fallback)` 표기로 추가. 근거 없으면 "코드에서 근거를 찾지 못했습니다"로 기록.

---

### STEP 6 — WebGL 공백 스캔 [병렬]

SDK 앵커와 무관하게 `#if` 플랫폼 분기 체인에서 WEBGL arm·`#else`가 없는 블록을 탐지한다.
STEP 1 완료를 기다리지 않고 즉시 실행 가능.

```bash
# 스크립트가 없으면 템플릿에서 복사
[ -f Docs/porting/h5-port-verify.py ] || cp $H5PW_ROOT/templates/scripts/h5-port-verify.py Docs/porting/

python3 Docs/porting/h5-port-verify.py \
  --platform {PLATFORM_SYMBOL} \
  --scripts {SCRIPTS_PATH} \
  --mode scan-void
# EXTRA_PATHS가 있으면 --scripts 를 반복 추가:
#   --scripts {EXTRA_PATH_1} --scripts {EXTRA_PATH_2}
```

`{PLATFORM_SYMBOL}`: `WEBGL_TOSS` 또는 `WEBGL_PUREWEB`.

출력 분류 및 처리 방침:

| Severity | 의미 | 처리 |
|---|---|---|
| `CONTROL_FLOW` | 루프 내 yield 없음 → 무한루프·프레임 정지 위험 | 파일:라인 Read 후 pureweb-checklist.md `## 이슈`에 `[런타임]` 항목으로 추가 |
| `STATE_UNDEF` | UI/상태 미정의 → 씬 기본값 의존 | 파일:라인 Read 후 pureweb-checklist.md `## 이슈`에 `[런타임]` 항목으로 추가 |
| `BEHAVIOR_GAP` | 동작 누락 — 의도된 공백 가능성 있음 | Read 확인 후 이슈 여부 판정. 네이티브 전용(GPGS·AndroidConnect 등)이면 기록 생략 |

`CONTROL_FLOW` · `STATE_UNDEF` 건수가 0이면 pureweb-checklist.md `## 이슈`에 `- [x] WebGL 공백 스캔 — 이상 없음 (CONTROL_FLOW·STATE_UNDEF 0건)` 한 줄을 기록한다.

---

### STEP 4 — 게임 구조 파악 [병렬]

**`Docs/porting/PORTING_VOCAB.md`가 존재하면** 파일을 읽어 그대로 사용. 아래 탐색 과정 생략.

**PORTING_VOCAB.md가 없으면** 2단계로 탐색한다.

#### 4-A. 파일명 휴리스틱으로 후보 탐색

```bash
find {SCRIPTS_PATH} -name "*.cs" 2>/dev/null \
  | grep -iE "(Ad|Store|IAP|Purchase|Sound|Audio|BGM|Save|Cloud|Network|Time|Login|User|Review|Rating)" \
  | grep -vE "Editor|Test|Sample|HyperLane" | sort
```

시스템별로 가장 유력한 파일 1~2개를 Read로 읽어 실제 메서드명을 확인한다.

#### 4-B. 게임 진입점 분석

```bash
# DontDestroyOnLoad — 앱 전역 초기화 오브젝트 후보
grep -rn "DontDestroyOnLoad" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | head -10

# 진입점 클래스명 후보 (GameRoot, GameManager, Boot, Launcher 류)
grep -rln "void Awake\|void Start" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -iE "GameRoot|GameManager|AppManager|Boot|Init|Launcher|Entry" | head -10
```

후보 파일을 Read해서 실제 초기화 흐름(씬 로드 → 첫 Awake/Start → 게임 시작 순서)을 확인한다. **이 흐름은 다음 4-C(기본 스캔)의 "첫시작로드" 판정에 그대로 쓰인다 — 4-C에서 다시 탐색하지 않는다.**

**로비/메인 진입점 (`{LOBBY_ENTRY}`)**

로그인 로그(`LogDailyLogin`) 삽입 지점이 되는, **로그인·데이터 로드 이후 로비/메인 화면이 정상 표시되는 시점**을 확정한다. 이 앵커가 비면 platform-porter 3-A가 grep 추측으로 떨어진다.

```bash
# 로비/메인 진입 콜백·메서드
grep -rn "OnEnterLobby\|OnLobbyEnter\|EnterLobby\|EnterMain\|OnHomeEnter\|LobbyScene\|MainScene\|HomeScene\|SceneMain" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10

# 씬 로드 완료 콜백 (로비/메인 전환 지점 식별용)
grep -rn "SceneManager.LoadScene\|LoadSceneAsync\|OnSceneLoaded\|ActiveSceneChanged" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10
```

히트 파일을 Read해서 **데이터 로드 완료 후 로비/메인이 실제로 표시되는 콜백·메서드**(파일:라인)를 확정한다.
→ PORTING_VOCAB.md `로비 진입점` 행에 파일:라인 기록. 앱 부팅 진입점(`{GAME_INIT_METHOD}`)과 구분한다 — 로비 진입점은 로그인·로드 **이후** 단계다.
판정 불가 시 `확인 필요`로 기록하고 미해결 항목으로 분류한다. **"없음" 임의 단정 금지.**

#### 4-C. 기본 스캔

Toss·PureWeb 양 플랫폼 모두 필요한 항목.

```bash
# IAP
grep -rln "IStoreListener\|InitializePurchasing\|ProcessPurchase" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane

# IAP 데이터 형식 — 카탈로그/상품 테이블 저장 방식 탐지
find . \( -name "*.json" -o -name "*.asset" -o -name "*.csv" \) 2>/dev/null \
  | grep -iE "shop|iap|product|catalog" | grep -vE "\.meta|HyperLane"
# .json 히트 → json / .asset 히트 → asset / .csv 히트 → csv / 없음 → hardcoded 또는 확인 필요

# 광고 — 보상형/전면 (Show 패턴으로 파일 탐색)
grep -rln "LoadRewardedAd\|ShowRewardedAd\|OnRewardedAd\|OnAdRewarded\|ShowInterstitial\|LoadInterstitial\|LoadAdMob\|LoadAd\b" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane

# 광고 — pre-load 존재 여부 (메서드명 불문, isLoaded 플래그 기반)
grep -rln "isLoaded\b\|adLoaded\|isReady.*[Aa]d\|adReady\|rewardReady\|isLoadedReward\|isLoadedInter" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```

위 grep 결과로 광고 파일이 나왔으면 Read해서 아래 항목을 판별하고 PORTING_VOCAB 비고에 기록한다:

**로드 패턴**

| 판별 기준 | 패턴 |
|---|---|
| Show 호출 시점에 Load도 함께 호출 (isLoaded 플래그 없음) | `패턴1: 로드→노출` |
| isLoaded 플래그 있고, closeCall 안에서 Load 재호출 | `패턴2: pre-load` |
| Load 호출 위치가 4-B에서 확정한 진입점 메서드 내부이거나 그 직후 흐름에 있음 | `첫시작로드: 있음` |

**실패 시 재로드 처리**

failCall에 재로드 로직이 있는지 확인한다. **failCall에서 재로드하는 것은 잘못된 패턴**으로 포팅 시 수정 대상.

| 판별 기준 | 기록값 |
|---|---|
| failCall 안에서 Load 재호출 없음, Show 시점에서 미완료 처리 | `실패재로드: Show시점` |
| failCall 안에서 Load 재호출 있음 (잘못된 패턴) | `실패재로드: failCall⚠️` |

**전면 광고 진입점 함수명 추출 (`{INTERSTITIAL_ENTRY}`)**

AD_MANAGER 파일에서 전면 광고를 실제로 표시하는 함수의 정의를 찾아 **실제 함수명**을 확정한다.  
→ PORTING_VOCAB.md `광고 전면 진입점` 행에 함수명 기록. 없으면 `없음`.

**전면 광고 쿨타임 변수 추출 (`{COOLTIME_VAR}`)**

```bash
grep -rn "forcedads\|interstitial_cool\|ad_cooltime\|ad_max" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v "//" | head -5
```

히트한 변수명 중 쿨타임을 나타내는 첫 번째 변수명을 확정한다.  
→ PORTING_VOCAB.md `전면 쿨타임 변수` 행에 변수명 기록. 없으면 `없음`.

**광고 중 게임 중지 여부** ❓

광고 표시 중 게임을 멈춰야 하는지 사용자에게 확인한다.
먼저 시간 제어 로직이 얼마나 퍼져 있는지 탐색해 판단 근거를 제공한다.

> **탐색 전 체크**: STEP 1에서 DOTween·UniTask·LeanTween 등이 확인됐으면 외부 라이브러리 grep도 함께 실행한다.

```bash
# TimeScale 제어 위치 — 광고 중 0으로 세팅하는 코드 파악
grep -rn "Time\.timeScale" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -15

# Coroutine 기반 타이머 — Time.timeScale=0에 멈추는 패턴 (게임중지:필요이면 수정 대상)
grep -rn "WaitForSeconds\b\|InvokeRepeating\|\.Invoke(" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -15

# Realtime 계열 타이머 — Time.timeScale=0 영향 없음 (수정 불필요)
grep -rn "WaitForSecondsRealtime\|unscaledDeltaTime\|unscaledTime\b\|realtimeSinceStartup" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10

# 프레임 기반 카운터 (Update의 deltaTime 누적 — Time.timeScale=0에 멈춤)
grep -rn "Time\.deltaTime\b" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v HyperLane | head -10

# 시스템 시간 / Stopwatch — timeScale 무관 (수정 불필요)
grep -rn "DateTime\.Now\|DateTimeOffset\b\|Stopwatch\b" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10

# 외부 라이브러리 Unscaled 설정 (STEP 1에서 DOTween·UniTask 확인된 경우만)
grep -rn "UpdateType\.UnscaledTime\|DelayType\.UnscaledDeltaTime\|useEstimatedTime" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -5
```

탐색 결과를 PORTING_VOCAB 광고 행 비고 컬럼에 `게임중지: 확인 필요`로 기록한다.
Coroutine 기반 타이머 히트 파일 목록도 함께 기록해둔다 (완료 후 사용자 확인 시 포터에 전달).

확정값(`게임중지: 필요` / `게임중지: 불필요`)은 완료 후 채팅 출력 단계에서 사용자 확인 후 기록한다.

```bash
# 저장/불러오기
grep -rln "PlayerPrefs\|BinaryFormatter\|File\.Write\|File\.Read" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane

# 서버 시간
grep -rln "UnityWebRequest\|DateTime\|TimeSpan" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -iE "Time|Server|Network" | grep -v HyperLane

# 앱 초기화 완료 플래그
grep -rn "isAppInitialized\|isInitialized\b\|LoadComplete\b" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -5
```

**IAA·IAP·저장 — WebGL 포팅 처리 현황**

4-C에서 확인된 IAA·IAP·저장 진입점의 WEBGL 가드 현황을 스캔한다.
코드 수정은 없다 — 결과는 PORTING_VOCAB.md 비고에 추가해 이후 포팅 작업 시 즉시 확인할 수 있게 한다.

```bash
# IAA — 보상형 광고: WEBGL 가드 없는 진입점
# {AD_REWARDED_METHOD}는 위 grep에서 확인한 실제 메서드명으로 대체
grep -rn "{AD_REWARDED_METHOD}" {SCAN_PATHS} --include="*.cs" 2>/dev/null \
  | grep -v "UNITY_WEBGL\|//"

# IAP — 결제: WEBGL 가드 없는 진입점
# {IAP_METHOD}는 위 grep에서 확인한 실제 메서드명으로 대체
grep -rn "{IAP_METHOD}" {SCAN_PATHS} --include="*.cs" 2>/dev/null \
  | grep -v "UNITY_WEBGL\|//"
```

결과를 PORTING_VOCAB.md 해당 행 비고 컬럼에 추가한다:

| grep 결과 | VOCAB 비고 추가 |
|---|---|
| 0건 | `WebGL 처리: ✅ 완료` |
| 1건 이상 | `WebGL 처리: ⬜ 미처리 — 포터에서 즉시지급 처리 필요` |

> Base64 인코딩 현황은 4-E 결과를 그대로 VOCAB에 반영한다 (별도 grep 불필요).

**Zero-Hit Fallback** — 시스템별 grep이 0건이면 해당 시스템에 한해 도메인 어휘로 후보를 찾는다 (최대 5개 파일, 1단계):

```bash
# IAP 0건 시
grep -rilnE "purchase|결제|상품|receipt|영수증|billing" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -vE "HyperLane|Test" | head -5
# 광고 0건 시
grep -rilnE "reward|보상|광고|incentiv|video.?ad|placement|adunit" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -vE "HyperLane|Test" | head -5
# 저장 0건 시
grep -rilnE "save|load|저장|불러|persist|serialize|repository" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -vE "HyperLane|Test" | head -5
```

후보 파일을 Read해 클래스 책임·진입점 메서드명(파일:라인)을 확인한다.
확인되면 VOCAB 해당 행에 `(fallback 확인: 파일:라인)` 표기. 판정 불가 시 `확인 필요 — fallback 후보: {파일목록}`으로 기록. **"없음" 임의 단정 금지.**

#### 4-D. Addressables 로드 시점 분석

```bash
# Addressables 사용 여부
grep -rln "Addressables\." {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v HyperLane | head -20
```

사용 파일이 있으면 Read해서 로드 시점을 파악한다.
- **초기화 시 로드** (게임 시작 전 일괄 로드) vs. **씬 전환·온디맨드 로드** 중 어느 패턴인지 구분
- 초기화 시 로드라면 H5Builder의 Addressables 빌드 통합과 충돌 여부 확인

판정 결과(`사용중`/`미사용` + 로드 패턴)는 VOCAB `에셋 현황` 행에 4-G(에셋 현황)의 오디오·텍스쳐 카운트와 함께 기록한다 — 이 행은 두 단계가 나눠 채운다.

#### 4-E. 저장 키 분석

**1단계 — 저장 방식 탐색**

```bash
# 저장 담당 클래스 후보 탐색
find {SCRIPTS_PATH} -name "*.cs" 2>/dev/null \
  | grep -iE "Save|Load|Data|Prefs|Storage|Record|Cloud" \
  | grep -vE "Editor|Test|Sample|HyperLane" | sort

# 저장 방식별 사용 여부 확인
grep -rln "PlayerPrefs\.\|File\.WriteAll\|BinaryWriter\|JsonUtility\.ToJson\|BinaryFormatter" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane

# 플러그인 기반 저장 (ES3 / Newtonsoft / SQLite)
grep -rln "ES3\.Save\|ES3\.Load\|ES3\.FileExists" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
grep -rln "JsonConvert\.SerializeObject\|JsonConvert\.DeserializeObject" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
grep -rln "SqliteConnection\|SqliteCommand" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```

**Zero-Hit Fallback** — 위 저장 패턴 전체 0건이면 영속 상태 경계를 찾는다 (최대 5개 파일, 1단계):

```bash
grep -rln "\[Serializable\]\|\[System\.Serializable\]" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -5
find {SCRIPTS_PATH} -name "*.cs" 2>/dev/null \
  | grep -iE "(Save|Load|Data|Storage|Repository|Cache|Profile|UserData|GameData)" \
  | grep -vE "Editor|Test|HyperLane"
grep -rn "this\[string\|SetValue\|GetValue" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -5
```

후보 상위 5개를 Read해 저장 매체·키 패턴·인코딩을 판정한다. VOCAB `저장 키`·`저장 인코딩` 행에 `(fallback)` 표기로 기록. 매체 불명확 시 `판정: 확인 필요`로 남기고 미해결 항목으로 분류.

**2단계 — 저장 담당 클래스 Read**

1단계에서 찾은 저장 담당 클래스를 Read해서 키/파일명 패턴을 확인한다.

확인 항목:
- 키가 하드코딩 문자열인지 (`"score"`, `"userData"` 등) → 게임별 prefix 없으면 충돌 위험
- 상수/enum으로 관리되는지 → 네이밍 규칙 확인
- 동적 생성 패턴인지 → 생성 규칙 확인 (예: `$"{gameId}_{key}"`)

**3단계 — 판정**

| 판정 | 조건 | 필요 조치 |
|---|---|---|
| 게임별 구분 있음 | prefix 또는 네임스페이스로 구분됨 | 없음 |
| 게임별 구분 없음 | 평문 키 (`"score"` 등) | pureweb-porter에서 키 분리 처리 필요 |
| 확인 필요 | 동적 생성 또는 외부 정의 | 생성 규칙 추가 확인 |

결과를 PORTING_VOCAB.md `저장 키` 행에 아래 형식으로 기록한다.

```
저장 방식: PlayerPrefs / File / BinaryWriter / ...
실제 키값 목록: "score", "userData", "level", ...  (확인된 키를 모두 나열)
판정: 게임별 구분 있음 / 없음 / 확인 필요
필요 조치: 없음 / pureweb-porter에서 키 분리 처리 / 생성 규칙 추가 확인
```

**4단계 — Base64 인코딩 / 암호화 여부 확인**

저장 담당 클래스에서 인코딩·암호화를 각각 확인한다.

```bash
# Base64 인코딩 여부
grep -rn "Convert\.ToBase64String\|ToBase64\|Base64Encode\|FromBase64\|EncryptPrefs" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10

# 암호화 여부 (AES, 커스텀 Encrypt 등)
grep -rn "AES\|Encrypt\|Decrypt\|Cipher\|CryptoStream\|RijndaelManaged" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10

# 데이터 직렬화 형식 (JSON / Binary / XML)
grep -rn "JsonUtility\.ToJson\|JsonConvert\.Serialize\|BinaryFormatter\|BinaryWriter\|XmlSerializer" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | head -10
```

결과를 PORTING_VOCAB.md `저장 인코딩` 행에 분리해서 기록한다:

```
데이터 형식: JSON (JsonUtility) / Binary (BinaryFormatter) / XML / key-value (PlayerPrefs 직접)
Base64 인코딩: 있음 (메서드명) / 없음 — 포팅 시 추가 필요
암호화: 있음 (방식: AES / 커스텀 / 기타) / 없음
```

#### 4-F. 자체 빌드 스크립트 분석

사전 감지에서 찾은 `BuildPlayer|BuildPipeline|IPreprocessBuildWithReport|IPostprocessBuildWithReport` 파일을 분석한다.

**파일이 있는 경우**: Read해서 아래 항목을 확인하고 NATIVE_BASELINE.md `자체 빌드 스크립트` 항목에 파일:라인으로 기록한다.
- PreBuild 단계 목록 (폰트 베이크, 아틀라스, 오디오 세팅, Addressables 빌드 등)
- H5Builder가 이미 처리하는 항목 vs. 이 프로젝트에서만 추가로 필요한 항목
- WebGL 빌드 메서드 존재 여부

**파일이 없거나 SDK 폴더(`Assets/GoogleMobileAds/Editor/`, `Assets/GooglePlayGames/Editor/` 등)에만 있는 경우**: 게임 직접 작성 빌드 스크립트 없음으로 판정. `자체 빌드 스크립트 | 없음` 으로 기록.
- SDK 내장 에디터 훅은 H5Builder 결정과 무관하므로 "있음"으로 처리하지 않는다.

#### 4-G. 에셋 현황

```bash
# 오디오 파일 수
find Assets -name "*.mp3" -o -name "*.wav" -o -name "*.ogg" 2>/dev/null | wc -l

# 텍스쳐 수
find Assets -name "*.png" -o -name "*.jpg" 2>/dev/null | grep -v HyperLane | wc -l
```

결과를 VOCAB `에셋 현황` 행에 기록: `오디오: N개 / 텍스쳐: N개 / Addressables: 사용중·미사용`(Addressables 값은 4-D에서 확정한 것을 그대로 씀).

#### 4-H. 기존 치트 코드 탐색

platform-porter 7-0(치트 — 서버/로컬 초기화)이 매번 처음부터 grep하지 않도록, 프로젝트에 이미 있는 치트/디버그 시스템을 미리 찾아둔다.

```bash
grep -rln "Cheat\|DebugConsole\|DevMenu\|GMMode\|CheatConsole" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```

- 결과 있음 → 파일:라인을 VOCAB `## 포터 기록`에 기록 (platform-porter 7-0이 읽기 참조)
- 결과 없음 → "없음"으로 기록

#### 4-I. 플랫폼 공통 · Toss 전용 스캔

> 플랫폼이 **Toss 또는 전체**인 경우에만 실행한다.

두 그룹으로 나눠 스캔한다. 각 항목은 grep으로 후보 파일을 찾은 뒤 **Read해서 실제 코드 위치(파일:라인)를 확정**한다 — 파일명 나열만으로 VOCAB 행을 채우지 않는다. **그룹마다 기록 대상 VOCAB 섹션이 다르다**:
> - **A. 플랫폼 공통** → VOCAB `## 플랫폼 공통` 섹션. 모든 WebGL 플랫폼에 동일하게 적용되는 HLSDK 로직이라 **platform-porter**가 읽는다.
> - **B. Toss 전용** → VOCAB `## Toss 전용` 섹션. TossHandler 직접 연동이 필요해 **toss-porter**만 읽는다.

##### A. 플랫폼 공통 (platform-porter 입력)

**햅틱/진동**
```bash
grep -rln "Vibrate\|Haptic\|haptic\|vibrate" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 진동 호출부(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `햅틱/진동` 행. 0건이면 `역기획 필요`로 기록한다.

**가격 표시 UI**
```bash
grep -rln "price\|Price\|productPrice\|priceText\|PriceText\|costText" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 가격 표시 클래스·`SetPrice` 존재 여부(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `가격 표시 UI` 행.

**랭킹**
```bash
grep -rln "Leaderboard\|LeaderBoard\|SubmitScore\|RankButton" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 랭킹 연동 클래스(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `랭킹 연동` 행. 없으면 "없음".

**공유하기**
```bash
grep -rln "NativeShare\|ShareLink\|OnClickShare" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 공유 호출부(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `공유하기` 행. 없으면 "없음".

**SafeArea 클래스**
```bash
grep -rln "SafeArea\|safeArea\|GetSafeArea\|SafeAreaInsets" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 클래스 위치(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `SafeArea 클래스` 행(있음/없음-신규필요).

**UID / version 표시**
```bash
grep -rln "version\|Version\|buildNumber\|AppVersion\|uid\|userId\|UserID\|GetUserKey\|userKey" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane | grep -iv "//.*version"
```
히트 파일을 Read해 표시 UI 위치(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `UID/version 표시` 행.

**불필요 UI 후보** (WebGL에서 숨겨야 하는 네이티브 전용 UI)
```bash
grep -rln "RestorePurchase\|Restore\|ContactUs\|RateApp\|StoreLink\|AppStore\|GooglePlay\|CrossPromo\|CrossPromotion\|FreeCache\|Anzu\|anzu\|CloudSave\|CloudLoad\|ICloudStorage" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 각 항목의 파일:라인을 확정 → VOCAB `## 플랫폼 공통` `불필요 UI 목록` 행에 **후보**로 기록(복수 가능). 제거 확정은 이 단계에서 하지 않는다 — platform-porter가 제거 전 사용자에게 확인한다(이슈 #44, 14번 이관).

**로컬라이제이션**
```bash
grep -rln "Localization\|LocalizationManager\|I2Loc\|GetSystemLang\|systemLanguage\|WebUtil.*Lang" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 클래스 위치(파일:라인)를 확정 → VOCAB `## 플랫폼 공통` `로컬라이제이션` 행. 없으면 "없음".

**리뷰 팝업** (플랫폼 무관 — 메인 표에 기록)
```bash
grep -rln "Review\|Rating\|StoreReview\|RequestReview" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 위치(파일:라인)만 메인 표 `리뷰 팝업` 행에 기록한다(위 두 섹션이 아니다). 발동조건은 여기서 분석하지 않는다 — pureweb-porter가 제거 직전에 파악해 pureweb-checklist `## 기획자 보고`에 테스트 항목으로 기록한다(플랫폼 무관 WebGL 공통 처리 — 이슈 #10). 결과가 없으면 → "없음"으로 기록.

##### B. Toss 전용 (toss-porter 입력)

**광고 — 배너**
```bash
grep -rln "BannerAd\|ShowBanner\|LoadBanner\|BannerView\|HideBanner\|DestroyBanner" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 배너 호출부(파일:라인)를 확정 → VOCAB `## Toss 전용` `배너 광고` 행. 없으면 "없음".

**프로모션**
```bash
grep -rln "ClaimPromotion\|PromotionReward\|promotionId" \
  {SCRIPTS_PATH} --include="*.cs" 2>/dev/null | grep -v HyperLane
```
히트 파일을 Read해 프로모션 트리거 위치(파일:라인)를 확정 → VOCAB `## Toss 전용` `프로모션 방식` 행에 위치만 기록(Managed/V1 판별은 toss-porter 12단계 담당).

#### 4-J. PORTING_VOCAB.md 저장

`Docs/porting/` 디렉토리가 없으면 `mkdir -p Docs/porting` 후 저장.

각 행의 플레이스홀더는 아래 템플릿 표 자체가 유일한 정의다 — platform-porter·toss-porter·pureweb-porter는 생성된 `PORTING_VOCAB.md`를 직접 읽어 `플레이스홀더` 열을 참조한다. 다른 문서(h5-port.md 등)가 이 목록을 별도로 재정의하지 않는다 — 재정의하면 이 템플릿과 어긋날 수 있다(드리프트).

> **`메서드/클래스명` 열은 실제 메서드명을 반드시 백틱으로 감싸 적는다** — `h5-port-verify.py`(`extract_methods`)가 정규식 `` `([^`]+)` ``로 백틱 안의 값만 추출한다. 백틱 없이 일반 텍스트로 적으면 STEP 4 검증 스크립트가 메서드명을 찾지 못해 조용히 통과(0건)로 오판한다.
> - 형식: `` `ClassName.MethodName()` `` (클래스명 없이 `` `MethodName()` ``도 가능)
> - 오버로드·유사 메서드 여러 개: `` `Class.ShowVideo_Continue/BossMode/Gem()` `` → `ShowVideo_Continue`·`ShowVideo_BossMode`·`ShowVideo_Gem` 3개로 분리 추출됨
> - 상속 선언(`` `Class : Interface` ``처럼 `:` 포함)은 파서가 자동 제외 — 메서드명 대신 상속 관계를 적는 용도로 쓰지 않는다

```markdown
# Porting Vocabulary — {프로젝트명}

| 시스템 | 메서드/클래스명 | 파일:라인 | 플레이스홀더 | 비고 |
|---|---|---|---|---|
| IAP | ... | ... | `{IAP_METHOD}` | |
| IAP 데이터 형식 | ... | ... | — | asset / json / csv / hardcoded / 확인 필요 |
| 광고 (보상형) | ... | ... | `{AD_REWARDED_METHOD}` | Load메서드명 / 패턴1·패턴2 / 첫시작로드: 있음·없음 / 실패재로드: Show시점·failCall⚠️ / 게임중지: 필요·불필요 |
| 광고 (전면) | ... | ... | `{AD_INTERSTITIAL_METHOD}` | Load메서드명 / 패턴1·패턴2 / 첫시작로드: 있음·없음 / 실패재로드: Show시점·failCall⚠️ / 게임중지: 필요·불필요 |
| 광고 전면 진입점 | ... | ... | `{INTERSTITIAL_ENTRY}` | 없으면 "없음" |
| 전면 쿨타임 변수 | ... | ... | `{COOLTIME_VAR}` | 없으면 "없음" |
| 저장 | ... | ... | `{SAVE_METHOD}` | 서버/클라우드 저장 진입 메서드 |
| 불러오기 | ... | ... | `{LOAD_METHOD}` | 서버/클라우드 불러오기 진입 메서드 |
| 로컬 저장 | ... | ... | `{LOCAL_SAVE_METHOD}` | 로컬 저장 함수명 (없으면 "확인 필요") |
| 로컬 불러오기 | ... | ... | `{LOCAL_LOAD_METHOD}` | 로컬 불러오기 함수명 (없으면 "확인 필요") |
| 서버시간 | ... | ... | — | 코루틴 여부 |
| 사운드 | ... | ... | `{SOUND_CLASS}` | 클래스명 |
| 앱 초기화 플래그 | ... | ... | — | bool 필드명 |
| 리뷰 팝업 | ... | ... | — | WebGL 제거 대상 |
| 게임 진입점 | ... | ... | `{GAME_INIT_METHOD}` | 첫 씬/클래스명, 초기화 순서 |
| 로비 진입점 | ... | ... | `{LOBBY_ENTRY}` | 로비/메인 정상 진입 콜백·메서드 (LogDailyLogin 삽입 지점). 없으면 "확인 필요" |
| Addressable 로드 시점 | ... | ... | — | 초기화 시 / 온디맨드 / 미사용 |
| 에셋 현황 | ... | ... | `{ASSET_COUNTS}` | 오디오: N개 / 텍스쳐: N개 / Addressables: 사용중·미사용 |
| 빌드 특이사항 | ... | ... | — | H5Builder 외 추가 PreBuild 단계 |
| 저장 키 | ... | ... | — | 저장 방식 / 키 패턴 / 게임별 구분 여부 |
| 저장 인코딩 | ... | ... | — | 데이터 형식: JSON/Binary/XML/key-value / Base64: 있음(메서드명) / 없음 — 포터에서 래핑 필요 / 암호화: 있음(방식)/없음 |

## 플랫폼 공통

> platform-porter가 읽는다 — 모든 WebGL 플랫폼(Toss/Kakao/CrazyGames)에 동일하게 적용되는 HLSDK 로직. (STEP 4-I A그룹)

| 시스템 | 파일:라인 | 플레이스홀더 | 비고 |
|---|---|---|---|
| 햅틱/진동 | ... | `{HAPTIC_FILE}` | 없으면 "없음" / 역기획 필요 |
| 가격 표시 UI | ... | `{PRICE_UI_CLASS}` | SetPrice 메서드 존재 여부 |
| 랭킹 연동 | ... | `{RANKING_FILE}` | 없으면 "없음" |
| 공유하기 | ... | `{SHARE_FILE}` | 없으면 "없음" |
| SafeArea 클래스 | ... | `{SAFEAREA_CLASS}` | 있음(파일명) / 없음-신규필요 |
| UID/version 표시 | ... | `{UID_VERSION_FILE}` | 있음(파일명) / 없음 |
| 불필요 UI 목록 | ... | `{REMOVE_UI_LIST}` | **후보** 파일:라인 목록 (복수 가능) / 없음 — 제거 확정은 포터가 사용자에게 확인 |
| 로컬라이제이션 | ... | `{LOCALIZATION_FILE}` | 있음(파일명) / 없음 |

## Toss 전용

> toss-porter만 읽는다 — TossHandler 직접 연동이 필요한 항목. (STEP 4-I B그룹)

| 시스템 | 파일:라인 | 플레이스홀더 | 비고 |
|---|---|---|---|
| 배너 광고 | ... | `{BANNER_FILE}` | 없으면 "없음" |
| 프로모션 방식 | ... | `{PROMOTION_TYPE}` | Managed / V1 / 없음 |

## 포터 기록

> 위치(파일:라인) 기록 전용 — 상태·완료 여부는 체크리스트(pureweb/toss-checklist.md)에 기록한다.

| 시스템 | 파일:라인 | 플레이스홀더 | 비고 |
|---|---|---|---|
```

확인하지 못한 시스템은 "확인 필요"로 표기.

햅틱/진동 grep 결과가 0건이면 → `역기획 필요`로 기록한다.

**VOCAB 저장 후 — 플레이스홀더 누락 체크**

위 매핑 테이블에 없는 행 중 실제 값이 채워진 항목이 있으면 사용자에게 보고한다:

> "아래 항목이 PORTING_VOCAB.md에 채워졌지만 플레이스홀더가 없습니다. h5-port.md에 추가가 필요할 수 있습니다:"
> - 서버시간: `{실제값}`
> - 앱 초기화 플래그: `{실제값}`
> - 광고 (배너): `{실제값}`
> - 리뷰 팝업: `{실제값}`
> *(값이 "없음" / "확인 필요"인 항목은 제외)*

---

### STEP 2 — 컴파일 이슈 탐색 [STEP 1 완료 후]

STEP 1에서 확보한 SDK 네임스페이스 목록으로 탐색한다.

```bash
# SDK 네임스페이스 using — UNITY_WEBGL 가드 없는 것
grep -rn "^using {SDK네임스페이스}" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null

# #if !UNITY_EDITOR 만 있고 UNITY_WEBGL 누락된 초기화 블록
grep -rn "UNITY_EDITOR" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v "UNITY_WEBGL\|//"

# SDK 타입 상속 (stub 클래스 필요 여부 재확인)
grep -rn ":\s*I[A-Z][a-zA-Z]*\b" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v "HyperLane\|//"
```

---

### STEP 5 — 문서 저장

`Docs/porting/` 디렉토리가 없으면 `mkdir -p Docs/porting` 후 아래 4파일을 저장한다 (형식은 "출력 문서 형식" 1~3 + VOCAB 참조):

NATIVE_BASELINE.md 헤더의 `기준 커밋`은 새로 캡처하지 않고, STEP 1에서 sdk-list-analyzer가 `.sdk-list.md`에 이미 기록해둔 값을 그대로 이어받는다 — 같은 스캔 흐름의 산출물들이 서로 다른 커밋을 기준점으로 갖지 않도록:

```bash
grep -oE "기준 커밋: [0-9a-f]+|NO_GIT" Docs/porting/.sdk-list.md | head -1
# .sdk-list.md가 없으면(예: BASELINE이 이미 있어 STEP 1에서 재분석 생략된 경우) 대체:
# git rev-parse HEAD 2>/dev/null || echo "NO_GIT"
```

1. `NATIVE_BASELINE.md` — 불변 스냅샷 (`## 외부 SDK 목록`은 STEP 1 수용본 기재)
2. `PORTING_VOCAB.md` — 위치 사전 (신규 또는 기존 갱신)
3. `pureweb-checklist.md` — 기반 작업목록 (STEP 2·3·6에서 발견한 이슈 포함)
4. `toss-checklist.md` — 플랫폼 작업목록

저장 성공 확인 후 임시 산출물을 삭제한다 (이중 진실 방지 — 정본은 NATIVE_BASELINE):

```bash
ls Docs/porting/NATIVE_BASELINE.md && rm -f Docs/porting/.sdk-list.md
```

---

## 출력 문서 형식 1 (`Docs/porting/NATIVE_BASELINE.md`)

포팅 전 네이티브 상태의 **불변 스냅샷**. porting-scan-verify 완료 후 동결 — 이후 갱신하지 않는다.
이슈·상태·진행은 여기 기록하지 않는다 (체크리스트 담당).

```markdown
# 네이티브 베이스라인 — {프로젝트 루트 폴더명}

> 생성일: {날짜} | 기준 커밋: {커밋 해시 | NO_GIT} | 스크립트 경로: {SCRIPTS_PATH} | 부속 경로: {EXTRA_PATHS 또는 "없음"}
> 포팅 전 네이티브 스냅샷 — scan-verify 후 동결. 이슈·진행 상태는 pureweb/toss-checklist.md 참조.

## 프로젝트 정보

| 항목 | 값 |
|---|---|
| Unity 버전 | {ProjectSettings/ProjectVersion.txt의 m_EditorVersion} |
| HyperLane SDK | 설치됨 / 미설치 |
| 빌드 씬 | ON N개 / OFF N개 / ❌ 누락 N개 |
| 자체 빌드 스크립트 | 파일:라인 또는 없음 |

---

## 외부 SDK 목록

| SDK | 용도 (추론) | 폴더 | jslib | 영향 파일 수 | 처리 방법 |
|---|---|---|---|---|---|
| Firebase | 인증·분석·푸시 | Assets/Firebase | 없음 | 12 | A |

---

## 게임 구조 (Docs/porting/PORTING_VOCAB.md 참조)

| 시스템 | 메서드/클래스명 | 파일:라인 |
|---|---|---|
```

---

## 출력 문서 형식 2 (`Docs/porting/pureweb-checklist.md` — 기반 작업목록)

**pureweb-porter가 처리하는 기반 포팅 이슈**(컴파일/런타임/공백)와 확인 필요를 기록한다. "WebGL에서 일단 돌게 만들기"에 해당하는 기반 작업이다.

> **라우팅 기준 — 어느 포팅 작업이 그 항목을 소비하는가** (분기 코드 존재 여부가 아니다):
> - **퓨어웹 포팅 작업이 소비** → 여기(pureweb-checklist). 컴파일/런타임/공백 이슈, 즉시지급 처리·서버저장 차단·SafeArea 등 퓨어웹 작업에 필요한 확인 필요.
> - **플랫폼(Toss) 포팅 작업이 소비** → toss-checklist. `WEBGL_TOSS` 전용 분기 이슈뿐 아니라 **광고·IAP 실동작 관련 확인 필요·기획자 보고**(로드 패턴·실패재로드·광고 중 게임중지·초기화 플래그·가격 UI·PID 매핑 등)도 포함 — 퓨어웹에서는 광고·IAP가 즉시지급으로 대체되어 이 항목들을 소비하지 않는다.
> - 판별 불가·양쪽 모두 소비 → 여기(기본).
>
> toss-checklist에는 기반 이슈를 기록하지 않는다 — toss-porter가 필요 시 이 `## 이슈`를 읽기 참조한다.

단계 진행 표는 여기 만들지 않는다 — pureweb-porter가 0-B에서 추가한다 (소유 분리).
상태 표기는 마크다운 체크박스: 완료 = `[x]` + `(commit 해시)` / 스킵 = `[x]` + `⏭️ 스킵: 사유` (사유 없는 스킵 금지).

```markdown
# PureWeb 포팅 체크리스트 — {프로젝트 루트 폴더명}

> 생성: {날짜} (porting-scan) | 단계 진행 표는 pureweb-porter가 추가

## 이슈

- [ ] {파일}:{라인} — [컴파일] {이슈} — {처리 방법}
- [ ] {파일}:{라인} — [런타임] {이슈} — {처리 방법}
- [ ] {파일}:{라인} — [공백:{Severity}] {분기 조건} — {처리 방법}

## 확인 필요

- [ ] {코드에서 직접 확인하지 못한 항목}

## 기획자 보고

- [ ] {포팅 시작 전·완료 후 기획자에게 전달할 항목}

## 교정 기록

(append-only — 스캔 오진·처리 실수와 교정 내용)

## 빌드 기록

| 날짜 | 빌드 타겟 | 파일 | 용량 | 비고 |
|---|---|---|---|---|
```

---

## 출력 문서 형식 3 (`Docs/porting/toss-checklist.md` — 플랫폼 작업목록)

**플랫폼(Toss) 포팅 작업이 소비하는 항목**을 담는다 (형식 2의 라우팅 기준 참조): `## 이슈`는 toss 전용(WEBGL_TOSS 분기) 이슈, `## 확인 필요`·`## 기획자 보고`는 광고·IAP 실동작 관련 항목(실패재로드·게임중지·가격 UI·PID 매핑 등) 포함. 기반(공통) 이슈는 여전히 pureweb-checklist가 정본이며 이 파일에 기록하지 않는다.
단계 진행 표는 toss-porter가 0-B에서 추가한다.

```markdown
# Toss 포팅 체크리스트 — {프로젝트 루트 폴더명}

> 생성: {날짜} (porting-scan) | 단계 진행 표는 toss-porter가 추가 | 기반 이슈: pureweb-checklist.md 참조

## 이슈

- [ ] {파일}:{라인} — [Toss전용] {이슈} — {처리 방법}

## 확인 필요

- [ ] {코드에서 직접 확인하지 못한 항목}

## 기획자 보고

- [ ] {항목}

## 교정 기록

(append-only)

## 빌드 기록

| 날짜 | 빌드 타겟 | 파일 | 용량 | 비고 |
|---|---|---|---|---|
```

---

## Stats Logging

`$H5PW_ROOT/templates/stats-logging-format.md`를 Read해서 그 형식을 따른다(agent-name은 `porting-scan`). STEP 5 저장 완료 후 기록한다.

추적 라벨(정규식은 각 STEP 본문 참조 — 여기서 재정의하지 않는다):

- **STEP 3 (런타임 7종)**: 네트워크(UnityWebRequest) · 파일IO · PersistentPath · 해상도고정 · SafeArea런타임 · 스레드/비동기 · OpenURL
- **STEP 4-B**: 진입점
- **STEP 4-C**: IAP매니저 · 광고보상형 · 광고전면 · 전면진입점 · 쿨타임변수 · 게임중지신호 · 저장패턴 · 초기화플래그
- **STEP 4-D**: Addressables
- **STEP 4-E**: 저장키
- **STEP 4-H**: 치트
- **STEP 4-I A (플랫폼 공통 → `## 플랫폼 공통`)**: 햅틱 · 가격UI · 랭킹 · 공유 · SafeArea클래스 · UID표시 · 불필요UI · 로컬라이제이션 (+ 리뷰팝업은 메인 표)
- **STEP 4-I B (Toss 전용 → `## Toss 전용`)**: 배너 · 프로모션

---

## 완료 후 채팅 출력

**STEP 5 실행 전 — 미해결 항목 확인**

fallback에서 `확인 필요` 또는 `근거 없음`으로 기록된 항목이 1건 이상이면, 문서 저장 후 AskUserQuestion을 호출한다:

> 질문: "스캔 완료 후 아래 항목을 코드에서 확인하지 못했습니다. 포팅 전에 직접 확인이 필요합니다.\n\n{항목별 시스템명 + 이유 목록}\n\n확인 후 포팅을 시작해 주세요."
> 옵션:
> - 확인 완료 — 포팅 진행합니다
> - 아직 확인 중 — 잠시 보류합니다

미해결 항목이 없으면 AskUserQuestion 없이 아래 완료 메시지만 출력한다.

---

```
✅ Docs/porting/NATIVE_BASELINE.md 생성 완료
✅ Docs/porting/PORTING_VOCAB.md 생성 완료  (신규 / 기존 파일 사용)
✅ Docs/porting/pureweb-checklist.md 생성 완료  (이슈 N건 기록)
✅ Docs/porting/toss-checklist.md 생성 완료

📊 요약
- 외부 SDK: N개 (jslib N개 포함)
- 컴파일 이슈: N건 (파일 N개)
- 런타임 이슈: N건

🔧 H5Builder 결정 필요 항목
- 자체 빌드 스크립트: {있음 — {파일:라인 목록} | 없음 — H5Builder만으로 충분}
  * 있음: H5Builder가 처리하지 않는 PreBuild 단계가 있으면 H5Builder 커스텀 필요
  * 없음: H5Builder 개선 불필요
- Addressables: {사용 중 ({에셋 수}개, 초기화 시 로드 / 온디맨드) | 미사용}
  * 사용 중: H5Builder Addressables 빌드 통합 필요 여부 확인
  * 미사용: H5Builder 개선 불필요

📋 포팅 전 확인 필요 (사용자 직접 검토)
아래 파일을 열어 내용을 확인하고, 수정이 필요한 항목은 직접 수정한 뒤 포팅을 시작해 주세요:

  Docs/porting/NATIVE_BASELINE.md     — 프로젝트 정보·SDK 목록 (불변 스냅샷)
  Docs/porting/pureweb-checklist.md   — 컴파일·런타임·공백 이슈 (작업목록)
  Docs/porting/PORTING_VOCAB.md       — 포터가 참조할 메서드·파일명 어휘 사전

확인 완료 후:
- 스캔 결과 검증: /porting-scan-verify
- 퓨어웹: /pureweb-porter 실행 후 /platform-porter
- 토스: /pureweb-porter → /platform-porter → /toss-porter 순서로 실행 (pureweb-porter가 항상 최우선, 이슈 #44)
```
