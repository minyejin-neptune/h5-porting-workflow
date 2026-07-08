---
name: iaa-analyzer
description: IAA 보상형·전면형 광고 구조(Placement, 보상, 조건, 일 제한, 쿨타임, 예외 규칙)를 코드에서 역추적해 Docs/design/IAA.md로 저장하는 에이전트. "IAA 정리", "광고 구조 분석", "보상형 광고 뽑아줘", "전면 광고 분석" 같은 요청에 사용.
tools: Read, Bash, Write
---

# IAA 분석 에이전트

코드에서 보상형·전면형 광고 구조를 역추적해 `Docs/design/IAA.md`로 저장한다.

> **추론 금지**: 코드에서 직접 확인한 사실만 기재한다. 이름·패턴·관례로 추측한 내용은 절대 쓰지 않는다. 확인 불가 시 "확인 필요"로 명시한다.
> **탐색 원칙**: grep 패턴은 진입점이다. 히트 여부와 무관하게 연결된 코드·클래스·호출부를 따라 탐색을 계속한다.

---

## 파일 저장 규칙

분석 완료 후 결과를 `Docs/design/IAA.md`로 저장한다. 디렉토리가 없으면 `mkdir -p Docs/design`으로 먼저 생성한다.

---

## PORTING_VOCAB.md 재활용

```bash
ls Docs/porting/PORTING_VOCAB.md 2>/dev/null && echo "EXISTS" || echo "NONE"
```

파일이 존재하면 아래 행을 읽어 중복 탐색 없이 재활용한다.

| PORTING_VOCAB 행 | 재활용 내용 |
|---|---|
| SCRIPTS_PATH | 스크립트 경로 확정 — 재탐색 불필요 |
| 광고 (보상형) | 파일:라인에서 AD_MANAGER 파일명 추출 — 재탐색 불필요 |
| 광고 (전면) | 파일:라인에서 AD_MANAGER 파일명 추출 (보상형과 같은 파일이면 중복 제거) |
| 광고 전면 진입점 | `{INTERSTITIAL_ENTRY}` — 기본 규칙 1에서 전면 진입점 함수명으로 직접 사용 |
| 전면 쿨타임 변수 | `{COOLTIME_VAR}` — 기본 규칙 2에서 쿨타임 변수명으로 직접 사용 |

재활용 항목은 IAA.md에 `(PORTING_VOCAB.md 기준)`으로 출처 표기.
PORTING_VOCAB.md가 없으면 아래 프로젝트 경로 자동 감지에서 직접 탐색한다.

---

## 포팅 이슈 기록 연동

분석 중 포팅 이슈가 발견된 경우에만 실행한다.

포팅 이슈는 가변 정보(예측→검증→처리로 진화)이므로 작업목록(체크리스트)에 기록한다. 불변 스냅샷(NATIVE_BASELINE.md)에는 기록하지 않는다.

```bash
ls Docs/porting/toss-checklist.md Docs/porting/pureweb-checklist.md 2>/dev/null
ls Docs/porting/PORTING_ANALYSIS.md 2>/dev/null
```

- **체크리스트 있음**: 기반 포팅 이슈는 **pureweb-checklist.md**의 `## 이슈`에 기록한다(섹션 없으면 생성). 발견한 광고 이슈가 `WEBGL_TOSS` 전용이면 toss-checklist로 보낸다. 이미 기록된 항목이 있으면 해당 항목에 연결해 업데이트한다.
- **체크리스트 없고 구 `PORTING_ANALYSIS.md`만 있음** (시점 분리 이전 프로젝트): 기존 방식대로 PORTING_ANALYSIS.md 이슈 테이블에 기록한다.
- **둘 다 없음**: 기록하지 않고 사용자에게 포팅 산출 문서가 없다고 알린다.

IAA.md에는 포팅 관련 내용을 일절 남기지 않는다.

---

## 프로젝트 경로 자동 감지

분석 시작 전 아래 항목을 확정한다. 파악 불가 항목은 사용자에게 질문한다.

**PORTING_VOCAB.md가 있는 경우** — 항목별 skip 여부:

| 항목 | skip 조건 | skip 시 동작 |
|---|---|---|
| `SCRIPTS_PATH` | vocab에 행 있음 | vocab 값 그대로 사용 |
| `AD_MANAGER` | vocab `광고 (보상형)` 또는 `광고 (전면)` 행에 파일:라인 기재됨 | 해당 파일명을 AD_MANAGER로 사용 |
| `SHOP_SYSTEM` | vocab에 해당 항목 없음 | 항상 아래 grep 실행 |

**PORTING_VOCAB.md가 없는 경우** (porting-scan 미실행) — 아래 전체 직접 탐색:

```bash
# SCRIPTS_PATH
find . -maxdepth 4 -type d -iname "*script*"

# AD_MANAGER — void 정의가 있는 파일 (호출부 제외)
grep -rln "ShowRewardAD\|ShowRewardedAd\|ShowInterstitialAD\|ShowInterstitial" . --include="*.cs"
```

**항상 실행 (vocab 유무 무관):**

```bash
# SHOP_SYSTEM — vocab에 없는 항목
grep -rln "forcedads\|interstitial_cool\|ad_cooltime\|ad_max" . --include="*.cs"
```

감지 결과를 사용자에게 한 번에 보여주고 확인받은 뒤 분석을 시작한다.

---

## 기획 영역 / 개발 영역 분리 원칙

### 기획 영역 — 표 본문·섹션 설명

기획자·사업팀이 읽는 영역. **아래 내용만** 기재한다.

- 조건·수치·UI 위치·시점·상황을 한국어로 기술
- Placement명, 보상 종류, 노출 조건, 일 제한, 쿨타임
- 코드 내용은 일절 기재하지 않는다

### 개발 영역 — 섹션 하단 `> **개발 참고**` 블록

각 섹션(##/###) **마지막 줄**에 blockquote로 삽입한다.

```
> **개발 참고**: [`파일명.cs:라인`](../상대경로/파일명.cs) — `클래스명.메서드명()` 설명
```

- 링크 경로는 `Docs/design/` 디렉토리 기준 상대 경로 (`../../Assets/Scripts/...`)
- 클릭 시 VS Code에서 파일이 열림. 라인은 `Ctrl+G → 라인번호`로 이동
- 참조가 여러 개인 경우 `/` 로 구분:
  ```
  > **개발 참고**: [`AdManager.cs:88`](../../Assets/Scripts/Ad/AdManager.cs) — `ShowRewardAD()` / [`AdManager.cs:102`](../../Assets/Scripts/Ad/AdManager.cs) — `ShowInterstitialAD()`
  ```

**예외 — 실패 시 처리(Failure Handling)**: 재시도 없이 단순 종료하는 수준을 넘어 여러 분기·side-effect가 있는 경우, 해당 섹션의 개발 참고 블록에는 파일:라인 링크 외에 3~5줄 코드 스냅을 코드 블록으로 함께 인용해도 된다. 기획 영역 본문에는 여전히 코드를 기재하지 않는다.

### 기획 영역에 절대 쓰지 않는 것

- 클래스명·함수명·파일명:라인번호
- 변수 할당식 또는 비교식 (`soldOut=false`, `StartBoostShown` 미완료 상태 등)
- enum·플래그 식별자 (예: `EventType.StageMap`)
- asset 내부 인덱스 값
- `&&`, `||` 같은 코드 연산자 → `AND`, `OR`로 대체

**변환 예시:**
- ❌ `soldOut=false` → ✅ "품절 상태가 아닐 때"
- ❌ `NoAds=true` → ✅ "광고 제거 상품 구매 유저"
- ❌ `(EventType.StageMap)` → ✅ "스테이지 맵 이벤트 진행 중"

---

## 보상형 광고 탐색 방법

```bash
# 1. 보상형 광고 타입 enum 탐색
grep -rn "enum AdRewardType\|enum RewardAdType" {SCRIPTS_PATH} --include="*.cs"

# 2. 광고 버튼 등록 전수 조회 (타입별 placement 목록)
grep -rn "AddListener.*AdRewardType\.\|ShowRewardAD.*AdRewardType\." {SCRIPTS_PATH} --include="*.cs" | grep -v "//"

# 3. 직접 호출 방식인 경우
grep -rn "ShowRewardAD\|ShowRewardedAd" {SCRIPTS_PATH} --include="*.cs" | grep -v "//" | grep -v "void ShowReward"

# 4. 일 제한 카운트 키 탐색
grep -rn "AddRecordCount\|GetRecordCount\|adMaxCountDaily\|DailyLimit" {SCRIPTS_PATH} --include="*.cs" | grep -i "ad\|reward" | grep -v "//"

# 5. 일 초기화 시점 탐색
grep -rn "ResetRecordCount" {SCRIPTS_PATH} --include="*.cs" | grep -i "ad\|reward"

# 6. NoAds 즉시 지급 경로 탐색
grep -rn "NoAds\|bFree\|isFree" {AD_MANAGER} | grep -v "//"

# 7. 실패 처리 콜백 탐색 (광고 로드 실패 / 시청 미완료)
grep -rn "onRewardResult.*false\|rewardFail\|AdFailed\|LoadFailed\|onVideoFailed\|rewardCancel" {SCRIPTS_PATH} --include="*.cs" | grep -v "//"

# 8. 보상형 광고 쿨타임 변수/키 탐색 — PORTING_VOCAB 미지원 항목이므로 항상 직접 탐색
grep -rn "rewardCool\|reward_cool\|RewardAdCooltime\|rewardVideoCool\|rewardad_cool" {SCRIPTS_PATH} --include="*.cs" | grep -v "//"
```

### 보상형 광고 검토 포인트

- 광고 타입 enum 값이 placement 문자열로 전달되는지 (`adType.ToString()` 등)
- `NoAds` 플래그가 true일 때 광고 없이 즉시 보상을 지급하는 코드 경로가 있는지
- 일부 placement가 `bFree = true` 조건(무료 지급)을 가지는지
- 실패 콜백(`onRewardResult(false)`)이 보상 미지급 이외의 side-effect를 일으키는지
- 샵 내 특정 placement에 일 제한 카운터(`RecordCount`)가 붙는지
- 보상형 광고에 쿨타임 변수/키가 존재하는지, 존재하면 몇 초이고 어떤 화면에서 참조되는지 — 없으면 "쿨타임 없음"으로 확정

---

## 전면형 광고 탐색 방법

```bash
# 1. 전면 광고 표시 함수 호출 지점 전수 조회
grep -rn "ShowInterstitialAD\|ShowInterstitial" {SCRIPTS_PATH} --include="*.cs" | grep -v "void Show\|//"

# 2. 전면 광고 노출 가드 조건 (함수 내부)
grep -n "NoInterstitialAds\|NoAds\|IsVipCheck\|removeads\|ABTest" {AD_MANAGER} | grep -v "//"

# 3. 전면 광고 트리거 플래그 설정 위치
grep -rn "IsContentsOpenShowAds\|isShowInterstitial\|canShowInter" {SCRIPTS_PATH} --include="*.cs" | grep -v "//"

# 4. 카운트 누적 위치 (N판마다 등의 조건 파악)
grep -rn "SetAdCntValue\|interstitialCount\|ShowInterstitialCnt" {SCRIPTS_PATH} --include="*.cs" | grep -v "//"

# 5. 쿨타임/최대 노출 횟수 Define 테이블 키 확인
grep -n "forcedads\|interstitial_cool\|ad_cooltime\|ad_max" {SHOP_SYSTEM} | grep -v "//"
```

### 전면형 광고 검토 포인트

- 노출 트리거가 "판 수", "선택 횟수", "화면 진입" 중 무엇인지
- 트리거 호출부가 실제 활성 코드인지 주석 처리되어 있는지 확인 — 주석이면 해당 모드는 미작동으로 표기
- 쿨타임이 있는지 없는지, 있다면 몇 초인지 명시 — 값이 테이블에 존재하더라도 적용 코드가 주석이면 "없음"으로 표기
- 쿨타임/최대 횟수 값이 코드 하드코딩인지 런타임 테이블 로드인지 (런타임 로드인 경우 실제 값은 `.asset` 파싱으로 확인)
- NoAds/VIP/ABTest 등 예외 조건이 어느 상품 구매·운영 설정과 연결되는지
- 전면 광고 직후 보상형 광고가 동시에 트리거될 수 있는 시점이 있는지

---

## 기본 규칙 탐색 방법

기본 규칙 항목은 함수명 하드코딩이 아닌 **의미 기반 탐색**으로 확인한다.  
보상형·전면형 탐색 방법 섹션을 먼저 실행한 뒤, 그 결과로 확정된 실제 진입점 함수명을 사용한다.

---

### 기본 규칙 1 — 보상형/전면형 동시 노출 가능 여부

"동시 노출"은 **두 광고가 한 흐름(같은 함수·콜백·프레임)에서 함께 호출되어 화면에 겹쳐 뜰 수 있는가**를 묻는다. "연속 노출"(한 광고가 닫힌 뒤 유저가 별도 액션을 해야 다른 광고가 뜸)과 반드시 구분한다.

아래 순서로 탐색한다. 함수명은 앞 섹션 grep 결과에서 확정된 것을 그대로 사용하며, 추측하지 않는다.

**Step 1: 보상형 광고 실제 진입점 전수 파악**

보상형 탐색 방법 섹션(#2·#3 grep)에서 히트한 함수명을 모두 수집한다.
→ 이 함수명들이 `REWARDED_ENTRIES` (예: `ShowRewardAD`, `ShowVideo`, `ShowVideoAd` 등)

**Step 2: 전면형 광고 진입점 + 호출부(래퍼) 파악**

PORTING_VOCAB.md `광고 전면 진입점` 행에서 `{INTERSTITIAL_ENTRY}` 값을 읽는다.
→ `없음`이면 전면 광고 미사용 — 기본 규칙 1 "동시 노출 경로 없음"으로 즉시 확정.

전면 진입점의 **호출부**를 전수 조회한다. 전면 광고는 보통 진입점 함수가 직접 노출되지 않고, **패널 닫기·판 종료 같은 래퍼 함수 안에서** 호출된다. 이 래퍼 함수를 반드시 식별한다.

```bash
# 전면 진입점 호출부 전수 조회 (정의부 제외) — 어떤 함수가 전면을 감싸 호출하는지 확인
grep -rn "{INTERSTITIAL_ENTRY}" {SCRIPTS_PATH} --include="*.cs" | grep -v "void \|public void\|//"
```

→ 히트한 각 라인이 속한 함수가 `INTERSTITIAL_TRIGGERS` (예: `ExitMuseumPanel`, `ExitMenuPanel` 등 패널 닫기 함수).

**Step 3: 보상형이 존재하는 화면과 전면 트리거 화면의 교집합 찾기**

- 각 보상형 진입점이 **어떤 화면·패널에 배치**되어 있는지 확인한다 (호출부 파일·함수로 판단).
- 그 화면을 닫는 함수가 Step 2의 `INTERSTITIAL_TRIGGERS`에 포함되는지 대조한다.
- 교집합이 없으면 → **동시·연속 모두 불가, "동시 노출 경로 없음"으로 확정**, 종료.

**Step 4: 교집합 화면에서 보상형 완료 콜백이 전면 트리거를 자동 호출하는지 확인**

교집합 화면의 **보상형 완료 콜백 함수 본문**을 Read해, Step 2에서 식별한 전면 트리거 함수(패널 닫기 등) 또는 전면 진입점을 **직접 호출하는지** 확인한다.

```bash
# 보상형 완료 콜백 본문에서 전면 트리거 래퍼 호출 여부 — 콜백 파일을 Read 후 직접 확인 권장
grep -n "{INTERSTITIAL_TRIGGER}\|{INTERSTITIAL_ENTRY}" {보상형_완료_콜백_파일} | grep -v "//"
```

**판정 기준:**
- 보상형 완료 콜백이 전면 트리거(또는 진입점)를 **자동 호출** → 같은 흐름에서 두 광고가 연달아 호출됨. 화면 겹침 가능성을 추가 확인 후 "동시 노출 가능" 여부 단정.
- 보상형 완료 콜백이 **자동 호출하지 않음**(유저가 별도로 패널을 닫는 등 추가 액션을 해야 전면이 뜸) → **"동시 노출 불가 (순차만 가능)"으로 확정**. 보상형 광고가 닫혀야 유저가 다음 액션을 할 수 있으므로 화면 겹침도 불가.
- 두 진입점이 서로 다른 화면·경로에만 존재 → "동시 노출 경로 없음 (분리 호출)".

추론으로 답하지 않는다. "가드가 없으니 가능할 수도", "SDK 내부 처리일 것이다" 같은 표현 금지. 위 플로우를 끝까지 타서 코드 경로의 존재/부재로만 판정한다.

**Step 5: "동시 노출 가능"으로 판정된 경우 우선순위 확인**

Step 4에서 "동시 노출 가능"으로 판정됐을 때만 실행한다. 두 광고 중 실제로 화면에 나타나는 쪽(우선순위)을 코드 경로로 판정한다.

```bash
# 전면/보상형 진입점 함수 내부에 "노출 중이면 무시" 가드가 있는지 확인
grep -n "{INTERSTITIAL_ENTRY}" {AD_MANAGER} -A 5 | grep -i "isshowing\|isplaying\|is.*showing"
```

**판정 기준:**
- 나중에 호출되는 쪽의 진입부에 "이미 광고가 노출 중이면 return" 형태의 가드가 있음 → **먼저 호출되는 광고가 우선순위** (가드로 나중 호출이 무시됨)
- 그런 가드가 코드에 없음 → 두 Show 호출이 모두 그대로 실행되며, 실제 화면 우선순위는 SDK/네이티브 레이어의 동작이라 **코드로 판정 불가 — "확인 필요"로 명시**한다. 추측하지 않는다.

---

### 기본 규칙 2 — 보상형 광고 시청 시 전면형 쿨타임 영향 여부

**Step 1: 쿨타임 관련 변수/키 확정**

PORTING_VOCAB.md `전면 쿨타임 변수` 행에서 `{COOLTIME_VAR}` 값을 읽는다.

**Step 2: 쿨타임 갱신 위치 탐색**

```bash
# 히트한 쿨타임 변수/키명으로 쓰기 위치 조회
grep -rn "{COOLTIME_VAR}" {SCRIPTS_PATH} --include="*.cs" | grep -v "//" | grep -v "\.cs:.*\.cs:"
```

히트한 라인이 보상형 완료 콜백 내부인지 확인 → 내부가 아니면 "영향 없음"으로 확정, 종료.

내부이면 해당 대입문을 Read로 직접 확인해 **어떤 값으로 바뀌는지**까지 특정한다:
- `0` 또는 현재시각으로 대입 → "쿨타임이 즉시 초기화되어 전면 광고를 바로 다시 노출 가능해짐"
- 기존 값에 시간을 더하는 대입(`+= N`, `+ N초` 등) → "쿨타임이 N초 연장됨"
- 별도 플래그로 일시 정지(`pause`, `stop` 등) → "쿨타임 타이머가 일시 정지됨"
- 위 패턴에 해당하지 않으면 실제 대입 코드를 근거로 그 내용을 그대로 서술한다.

**Step 3: 쿨타임 변수가 없는 경우**

`{COOLTIME_VAR}`가 `없음`이면 → 쿨타임 기능 자체가 없음. "전면형 광고 쿨타임 없음"으로 기재.

---

### 기본 규칙 3 — 광고 로드 실패 시 자동 재시도

코드 확인 없이 기획 원칙 그대로 출력한다 (출력 원칙 기존 항목 참조).

---

## 출력 템플릿

```markdown
**기본 규칙 / Basic Rules**

- 보상형/전면형 광고 동시 노출 가능 시점일 경우 우선순위 / Ad priority when rewarded and interstitial can display simultaneously: 없음 / 있음 — (있으면 보상형·전면형 중 어느 쪽이 우선인지 1줄로)
- 보상형 광고 시청 시 전면형 광고 쿨타임 영향 여부 / Whether rewarded ad viewing affects interstitial cooldown: 없음 / 있음 — (있으면 어떤 영향인지 서술)

**보상형 광고 / Rewarded Ads**

| Placement | Reward Type | Condition | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

- 쿨타임 규칙 / Cooldown Rules: 없음 / 있음 — N초
- 일 제한 / Daily Limit: 없음 / 있음 — N회 (Placement마다 다르면 "표 참조" + 하단 소표)
- 실패 시 처리 / Failure Handling: 없음 / 있음 — 서술

---

**전면형 광고 / Interstitial Ads**

- 노출 위치 / Placement:
- 노출 규칙 / Display Rules:
  - 최초 노출 조건: (수학 기호 + 컨텐츠명, 예: 레벨 > 4 AND 스테이지 번호 >= 4)
  - 이후 반복 규칙: (N판마다 / 쿨타임 등 반복 트리거)
- 쿨타임 규칙 / Cooldown Rules: 없음 / 있음 — N초
- 실패 시 처리 / Failure Handling: 없음 / 있음 — 서술
- 예외 규칙 / Exception Rules (유저 상태 기반 예외만 — 최초 노출 타이밍은 위 노출 규칙에 기재):
  - (예) 광고 제거 상품 구매 유저
  - (예) 튜토리얼 미완료 유저

```

**출력 원칙:**
- 테이블 행은 Placement 하나당 한 행. 값이 확인되지 않으면 "확인 필요"가 아니라 반드시 코드를 파고들어 확인 후 기재한다. 끝까지 찾지 못한 경우에만 "코드에서 근거를 찾지 못했습니다"로 명시한다.
- Condition·Notes 열에는 기획자 언어(상황·수치·조건)만 기재한다. 변수명·클래스명·enum·플래그 등 코드 내용은 기재하지 않는다.
- 쿨타임 규칙 / 일 제한 / 실패 시 처리는 Placement 공통 규칙이면 테이블 아래 bullet, Placement별로 다르면 Notes 열에 기재한다.
- 일 제한이 Placement마다 다르면 본문에 `Placement | Daily Limit` 소표를 만들고, `- 일 제한 / Daily Limit:` 줄에는 값 대신 "표 참조"라고만 기재한다.
- 기본 규칙 1·2, 쿨타임 규칙, 일 제한, 실패 시 처리는 "없음" 또는 "있음 — 서술" 형식으로 기재한다. 빈칸으로 남기지 않는다.
- 전면형 노출 규칙의 최초 노출 조건은 말로 풀어쓰지 않고 수학 기호로 표기한다. 단, 코드 변수명이 아니라 컨텐츠 이름을 쓴다. (예) `레벨 > 4 AND 스테이지 번호 >= 4`
- 기본 규칙의 세 번째 항목("로드 실패 시 자동 재시도 금지")은 기획 원칙이므로 코드 확인 없이 그대로 출력한다.
- "동상" 같은 약어 사용 금지 — 반복 조건도 전체를 다시 기재한다.
- **포팅 주의사항(`⚠️ WebGL 포팅 주의사항` 등 개발 관련 내용)은 IAA.md에 기재하지 않는다.** 포팅 이슈 발견 시 처리 방법은 `## 포팅 이슈 기록 연동` 섹션을 따른다.

---

## Stats Logging

`~/github/h5-porting-workflow/templates/stats-logging-format.md`를 Read해서 그 형식을 따른다(agent-name은 `iaa-analyzer`). `Docs/design/IAA.md` 저장 완료 후 기록한다.

추적 대상 패턴 (보상형):
- `enum AdRewardType / RewardAdType` — 광고 타입 enum
- `AddListener.*AdRewardType / ShowRewardAD.*AdRewardType` — 버튼 등록
- `ShowRewardAD / ShowRewardedAd` — 직접 호출
- `AddRecordCount / GetRecordCount / adMaxCountDaily` — 일 제한 카운터
- `ResetRecordCount` — 일 초기화
- `NoAds / bFree / isFree` — 즉시 지급 분기

추적 대상 패턴 (전면형):
- `ShowInterstitialAD / ShowInterstitial` — 전면 광고 호출
- `NoInterstitialAds / IsVipCheck / ABTest` — 예외 가드
- `IsContentsOpenShowAds / isShowInterstitial` — 트리거 플래그
- `SetAdCntValue / interstitialCount` — 카운트 누적
- `forcedads / interstitial_cool / ad_cooltime` — 쿨타임 Define
