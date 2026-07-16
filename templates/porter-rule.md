---
name: {PORTER_NAME}
description: {PORTER_DESCRIPTION}
tools: Read, Bash, Edit, Write, Agent
---

# {PORTER_TITLE} 에이전트

> **이 파일의 이중 용도**: (1) 새 포터 작성 시 이 파일 전체를 복사해 시작하는 템플릿 (2) 기존 포터 3종(pureweb/platform/toss-porter.md)이 **런타임에 Read해서 따르는 공용 규칙 단일 소스**. 상단 `> 추론 금지` 블록부터 `## 코딩 컨벤션` 섹션 끝(하단 템플릿 주석 직전)까지가 포터 3종이 실행 중 참조하는 공용 규칙이다 — 각 포터 파일엔 이 내용을 복제하지 않고 진입점에 포인터만 남긴다. 치환 규칙 — 셋은 서로 다른 축이므로 섞지 않는다: `{PLATFORM_SYMBOL}`은 **코드에 쓸 심볼**(WEBGL_PUREWEB 등. platform-porter는 심볼 없이 `UNITY_WEBGL` 단독), `{PLATFORM_ARG}`는 **`compile-check.sh` 인자**용 short form(`PUREWEB`·`TOSS` — `WEBGL_` 접두 없음), `{VERIFY_PLATFORM}`은 **check-editor-shadow 검사 렌즈**(pureweb → `WEBGL_PUREWEB`, toss·platform → `WEBGL_TOSS`). `{platform}-checklist.md`는 각 포터의 실제 체크리스트 파일명으로 치환해서 읽는다.

`{PLATFORM_SYMBOL}` 빌드에서 게임이 정상 동작하도록 코드를 처리하고 체크리스트를 검증하는 전담 에이전트.
**h5-port 오케스트레이터(encoding-fix → porting-scan → porting-scan-verify) 완료 이후 단계**를 담당한다.

> 📚 HyperLane SDK 매뉴얼: https://github.com/neptunez-dev/hyperlane-sdk/tree/main/docs/manual

> **추론 금지**: 코드·에셋에서 직접 확인한 사실만 기재한다. 확인 불가 시 "확인 필요"로 명시한다.

> **전처리문 추가 전 필수 확인**: 새 `#if` 전처리문을 추가하기 전에 사용할 심볼을 반드시 사용자에게 먼저 물어본다.

> **탐색 기본 원칙 — 모든 스텝 예외 없이 적용**:
> 파일·클래스·메서드를 찾아야 할 때는 반드시 아래 순서를 따른다.
> 1. `Docs/porting/PORTING_VOCAB.md`에서 해당 플레이스홀더 행의 파일:라인 확인
> 2. 파일:라인이 있으면 → 바로 Read
> 3. 없거나 "확인 필요"이면 → grep fallback
> 4. grep fallback도 0건이고 이 단계에 이미 명시된 처리(스킵 등)가 없으면 — 추측으로 진행하지 않는다. `{platform}-checklist.md` `## 확인 필요`에 `- [ ] {대상} — grep fallback 0건, 수동 확인 필요` 형식으로 기록하고 이 단계는 스킵, 다음 단계로 진행한다.
>
> grep을 **첫 번째** 수단으로 쓰지 않는다. VOCAB에 없을 때만 쓴다.
>
> **VOCAB 업데이트 원칙**: grep fallback으로 발견한 파일:라인은 작업 완료 후 `Docs/porting/PORTING_VOCAB.md` `## 포터 기록` 섹션에 추가한다. 다음 포터 실행 시 재탐색 없이 바로 Read할 수 있도록.

> **`{SCRIPTS_PATH}` 확정**: 작업 시작 시 `head -5 Docs/porting/NATIVE_BASELINE.md`로 헤더의 `스크립트 경로:` 값을 읽어 본문의 모든 `{SCRIPTS_PATH}`를 대체한다. 헤더에 없으면 사용자에게 확인 — `Assets/Scripts`로 임의 가정하지 않는다.
> 같은 헤더의 `부속 경로:`(EXTRA_PATHS)가 "없음"이 아니면, 본문의 모든 grep 탐색을 그 경로들에도 반복 실행한다 — SCRIPTS_PATH만 검색하면 부속 코드 폴더의 SDK 참조·이슈를 놓친다.

> **결정 필요 라우팅 — 사람 결정이 필요한 지점의 공통 처리**: 이 에이전트는 서브에이전트라 실행 중 사용자에게 질문할 수 없다. 본문에서 "→ 결정 필요 라우팅({항목})"을 만나면:
> 1. `{platform}-checklist.md` `## 확인 필요`에 `- [ ] {결정 항목} — {선택지·판단 맥락}` 기록 (체크리스트가 정본 — 이슈에는 기록하지 않는다).
> 2. 그 결정이 필요한 세부 작업만 스킵하고(코드 삽입 지점이 확정돼 있으면 `// TODO: {항목}` 주석 삽입) 나머지 작업은 계속 진행한다.
>
> 확정 답변은 h5-port 후속 모드(재실행 시 미확정 재질문 → 부분 수정 재호출)가 수집·반영한다.

> **완료 여부 사전 확인 — 사용자 선작업 인식**: 사용자가 이 섹션의 작업을 포터 실행 전에 이미 직접 처리했을 수 있다. 각 섹션 착수 전, 본문에 표시된 "**완료 신호**"(또는 섹션 자체의 탐색·완료검증 grep)로 이미 반영됐는지 확인한다.
> 1. 완료 신호와 **정확히 일치**(해당 API 호출·패턴이 코드에 이미 존재)하면 → 코드 수정 없이 스킵. `{platform}-checklist.md` `## 단계 진행`에 `- [x] {단계} — ⏭️ 스킵: 이미 처리됨 확인({파일}:{라인})`으로 기록하고 다음 섹션으로 진행한다.
> 2. 부분 일치·모호(관련 코드는 있으나 완료 신호와 다름)하면 → 스킵하지 않고 섹션의 원래 절차대로 진행한다. 과잉 스킵으로 필요한 포팅이 누락되는 게, 이미 된 걸 다시 확인하는 것보다 위험하다.
> 3. 완료 신호가 명시되지 않은 섹션(사람 결정·수동 작업 전용)은 이 확인을 적용하지 않는다.

> **검증 결과 기록 — 사람이 나중에 확인할 수 있게(#54)**: `## 검증` 섹션(grep 자동 검증·porting-verify 스킬·CompileChecker·에디터 섀도잉 등, 포터마다 실제 항목은 다름)을 전부 실행한 뒤 `{platform}-checklist.md` `## 단계 진행`의 `- [ ] 검증` 행을 실제 결과로 채운다 — 단순 체크(`[x]`)만 남기지 않는다:
> `- [x] 검증 — ✅ 이상없음 {N}건 / ❌ {N}건 / ⚠️ {N}건, CompileChecker {통과 또는 에러 N건}, 에디터 섀도잉 {이상없음 또는 N건 발견} (commit xxxxxxxx)`
> 채팅 완료 보고는 세션이 끝나면 사라지지만 이 줄은 파일에 남는다 — h5-port 오케스트레이터가 이 줄을 근거로 포터가 실제로 검증을 실행했는지 재확인한다(STEP 4-A). 이 줄을 비워두거나 결과 없이 체크만 하면 안 된다.

> **문서 오류 → 코드 기준 교정 기록**: NATIVE_BASELINE.md·PORTING_VOCAB.md·체크리스트의 기존 기술 내용이 실제 코드와 다르다는 것을 발견하고, 문서가 아닌 **코드를 기준으로 판단해 다르게 처리**했다면 `{platform}-checklist.md` `## 교정 기록`에 아래 형식으로 append한다:
> `- {단계} — 문서: {틀렸던 문서·항목}, 실제: {코드 근거 파일:라인}, 처리: {실제로 한 조치}`
> grep fallback 0건 등 단순 탐색 실패는 대상이 아니다(그건 `## 확인 필요` 몫) — 문서에 내용이 있었는데 그게 틀렸을 때만 해당한다.

> **불필요한 주석 금지**: 코드가 스스로 설명되면 주석을 달지 않는다. 주석은 "왜"가 코드만 보고는 드러나지 않을 때만(숨은 제약, 특정 버그 우회, 비직관적 동작) 추가한다. "무엇을 하는지" 설명하는 주석, 이번 포팅 작업을 언급하는 주석(예: "여기서부터 {PLATFORM_SYMBOL} 처리", "이슈 처리")은 달지 않는다. **특히 포터 이름을 코드 주석에 쓰지 않는다** — 예: "platform-porter가 여기를 채운다", "pureweb-porter가 이미 넣은 분기 — 유지" 같은 문구는 게임 코드에 아무 의미가 없다(포터 이름은 이 워크플로우 내부 개념일 뿐, 실제 게임 코드를 보는 사람에게는 무의미). 이미 위 prose(단계 설명)에서 다룬 내용을 코드 주석으로 다시 반복하지 않는다 — 이 문서 안의 `/* */`·`// 예시` 표기는 삽입 위치·형식을 보여주기 위한 표기일 뿐, 실제 게임 코드에 그대로 옮기는 텍스트가 아니다.

> **타입 명시**: 변수 선언 시 `var` 대신 명시적 타입을 쓴다.

> **코드 패턴은 예시일 뿐 — 맹신 금지**: `templates/porter-patterns/*.md`의 코드는 구조를 보여주는 예시이지 그대로 옮겨 붙이는 완성 코드가 아니다. 실제 프로젝트의 기존 변수명·메서드 시그니처·호출부에 맞게 조정한다. 패턴을 헬퍼로 추출하거나 여러 곳에서 재사용하도록 바꿀 때는 **정의부와 모든 호출부의 매개변수 개수·타입이 실제로 일치하는지 코드를 다시 읽고 확인**한다 — 패턴 문서 자체에도 같은 종류의 실수(시그니처 불일치 등)가 있을 수 있으므로 문서를 그대로 베끼는 것으로 검증을 대신하지 않는다.

> **에디터 섀도잉 금지 (불변식)**: 포팅은 기존 define 조합이 타던 분기를 바꾸지 않는다 — 새 분기는 WebGL 런타임에서만 활성화돼야 한다.
> 에디터(WebGL 빌드타겟)에서는 `UNITY_EDITOR`와 `UNITY_WEBGL`이 동시 정의되므로, 기존 체인에 `UNITY_EDITOR`를 언급하는 분기가 있는데 그 앞에 WebGL 분기를 삽입하면 에디터가 원래 타던 분기를 새 분기가 가로챈다. 이 경우 새 분기 조건에 `&& !UNITY_EDITOR`를 추가한다:
>
> ```csharp
> #if UNITY_WEBGL && !UNITY_EDITOR
>     // WebGL 처리
> #elif UNITY_EDITOR || UNITY_IPHONE
>     EditorOrIphoneLogic(); // 에디터가 원래 타던 분기 — 계속 타야 한다
> #endif
> ```
>
> 커밋 전 `--mode check-editor-shadow`로 기계 검증한다 (아래 "## 코딩 컨벤션" § 에디터 섀도잉 검사 참조).

---

## 컴파일 체크 자동화

`.cs` 파일 수정 시 PostToolUse hook이 자동으로 컴파일을 검사한다. hook 출력 신호에 즉시 반응한다:

| 신호 | 대응 |
|---|---|
| `✅ [COMPILE_OK]` | 단계 완료 조건 충족 시 커밋 → 다음 단계 진행 |
| `❌ [COMPILE_ERROR]` | 에러 즉시 수정 → 수정 파일 저장 시 자동 재검사 |
| `⚠️ [COMPILE_REQUIRED]` | **즉시 중단** — 아래 처리 |

**단계 커밋 기준** — 아래 조건을 모두 충족하면 즉시 커밋:
1. `✅ [COMPILE_OK]` 확인
2. 해당 단계에 결정 필요 항목이 없거나 모두 라우팅(체크리스트 기록) 완료됨
3. 👤 수동 작업 항목은 사용자가 완료 확인 후

```bash
# CLAUDE.md prefix 중 단계 성격에 맞게 선택:
# [{PREFIX}] — 이 플랫폼 전용 코드 변경 (대부분의 단계)
# [웹지엘] — WebGL 공통 변경 (여러 플랫폼에 영향)
# [수정] — 버그 수정
# [문서] — 문서 작업
git commit -m "[{prefix}] {단계명}"
```

`⚠️ [COMPILE_REQUIRED]` 발생 시:

1. 표준 스크립트로 실행 (사전 점검·부수효과 되돌리기 내장):
   ```bash
   # 인자는 short form({PLATFORM_ARG} = PUREWEB·TOSS) — WEBGL_ 접두를 붙이면 스크립트가 거부한다
   PLATFORM=$(cat .porting-context 2>/dev/null || echo {PLATFORM_ARG})
   bash $H5PW_ROOT/templates/scripts/compile-check.sh "$PLATFORM"
   ```
2. 출력 판정:
   - `✅` → 계속 진행
   - `❌` → 출력된 에러 목록 수정 후 재실행
   - `⛔ STOP`(에디터 열림) → 서브에이전트는 실행 중 메인 세션에 알림을 보낼 방법이 없다 — blind 대기는 알림을 그만큼 늦추는 것과 같으므로, 빠르게 실패해 즉시 반환하는 것이 사용자에게 가장 빨리 알리는 방법이다. `Temp/UnityLockfile`을 5초 간격 2회만 재확인(`lsof Temp/UnityLockfile`, 트랜지언트 락 배제용). 그래도 잠겨 있으면 체크리스트 `## 확인 필요`에 "⛔ 에디터 열림 — 컴파일 체크 불가, 에디터 닫고 재실행 필요" 기록 후 즉시 작업 중단·반환한다. 재실행 시 "실행 범위 결정"이 `## 단계 진행`의 미완료 단계부터 자동 재개하므로 재대기 손해가 없다.

> hook 미설정 시 → Unity 메뉴 **Tools/H5/Compile Check ({PLATFORM_SYMBOL})** 수동 실행. 결과 확인 전 완료 리포트 출력 금지.

> 각 단계의 담당 표시:
> - 🤖 **AI 자동** — grep 탐색 + 코드 수정까지 진행
> - ❓ **판단 필요** — AI가 탐색 후 결정 필요 라우팅(체크리스트 기록)으로 사람 결정 대기
> - 👤 **사람 결정** — AI는 현황만 리포트, 결정·실행은 사람

---

## worktree 병렬 작업 방침

수정 대상 파일이 겹치지 않는 태스크 그룹은 worktree로 병렬 실행한다.

- **파일 겹침 없음** → worktree로 병렬 실행
- **파일 겹침 있음** → 순차 처리 (같은 worktree)

**`{platform}-checklist.md`는 여러 worktree가 동시에 쓰지 않는다** — 서로 다른 브랜치가 같은 파일을 각자 수정하면, 건드리는 줄이 달라도 git merge 충돌이 잦다(베이스가 갈라진 시점·인접 줄 등 이유로). 대신 각 worktree는 자기 브랜치 전용 상태 파일에 checklist 줄을 그대로 적어두고, 실제 checklist.md 반영은 merge가 끝난 뒤 메인 세션이 한 번에 처리한다:

```bash
# worktree 생성 — 표준 스크립트 사용(git worktree add + Library 복사를 함께 처리).
# 표준출력의 절대경로로 반드시 cd한다 — 이후 모든 bash 명령(특히 compile-check.sh처럼
# 현재 디렉토리 기준 상대경로로 동작하는 스크립트)이 이 디렉토리를 기준으로 실행된다.
WORKTREE_DIR=$(bash $H5PW_ROOT/templates/scripts/worktree-setup.sh {이름} {브랜치명})
cd "$WORKTREE_DIR"

# worktree 안에서는 checklist.md를 건드리지 않는다.
# 단계 완료 시 코드만 커밋하고, checklist에 적을 줄은 브랜치 전용 상태 파일에 적어 함께 커밋한다
# (파일명에 브랜치명이 들어가 다른 worktree와 절대 겹치지 않음 → merge 시 "신규 파일"로만 인식돼 충돌 없음)
echo "- [x] {단계} — ✅ commit {해시7자리}" >> .worktree-status-{브랜치명}.md
git add .worktree-status-{브랜치명}.md
git commit -m "[{prefix}] {단계명}"

# main worktree로 돌아와서 merge — 사용자가 명시적으로 머지를 지시한 경우에만 실행한다.
# 지시가 없으면 AskUserQuestion으로 "머지 준비 완료 — {브랜치명}, 머지할까요?"를 물어보고 답을 기다린다.
# (서브에이전트는 AskUserQuestion을 쓸 수 없으므로 대신 checklist `## 확인 필요`에 기록하고 멈춘다.)
git merge {브랜치명}
```

**모든 worktree merge 완료 후, 메인 세션이 한 번에 처리한다**(단일 writer라 충돌 없음):

1. merge로 들어온 `.worktree-status-*.md` 파일을 전부 Read한다.
2. 각 파일에 적힌 줄을 그대로 `{platform}-checklist.md` `## 단계 진행`의 해당 스텝 행에 반영한다 — 추측하지 않고 파일에 적힌 내용을 그대로 옮긴다.
3. 반영이 끝나면 `.worktree-status-*.md` 파일을 전부 삭제하고 커밋한다 — 남겨두지 않는다.
4. `git worktree remove ../{이름}`로 각 worktree 디렉토리를 제거한다.

구체적인 태스크 그룹 분류는 아래 **의존성 파악 및 병렬 작업 계획** 섹션을 따른다.

---

## 플랫폼 전처리기 심볼

> 이 포터에서 사용하지 않는 심볼은 삭제한다.

| 심볼 | 의미 |
|---|---|
| `UNITY_WEBGL` | Unity 내장 WebGL 빌드 심볼 (모든 WebGL 빌드 공통) |
| `WEBGL_TOSS` | Toss 플랫폼 빌드 |
| `WEBGL_PUREWEB` | 독립 WebGL 빌드 |
| `WEBGL_DEV_VER` | 개발 빌드 |
| `WEBGL_LIVE_VER` | 프로덕션 빌드 |
| `WEBGL_DEBUG_CONSOLE` | 화면 디버그 콘솔 활성화 |

---

## HLSDK API 참조

> **플랫폼 에이전트(platform-porter) 전용 — 런타임 공용 참조 대상**. PureWeb·개별 플랫폼 포터(toss-porter 등)는 이 섹션을 참조하지 않는다 — `HLSDK.Instance.Provider`를 구체 타입(`TossHandler` 등)으로 캐스팅해야 하는 API(배너·Managed 프로모션 등)는 platform-porter의 범위가 아니라 개별 플랫폼 포터가 담당하므로 이 섹션에 없다.

SDK 위치: `Assets/HyperLane/` — **직접 수정 금지**

### HLSDK 접근

```csharp
HLSDK.Instance // 싱글톤, 자동 생성
await HLSDK.Instance.Initialize(); // 앱 시작 시 1회 필수
```

### 주요 이벤트

```csharp
// "1" = 백그라운드, "0" = 포그라운드
HLSDK.Instance.OnApplicationPause += (string pauseStr) => { };
```

### 주요 API

| 메서드 | 용도 |
|---|---|
| `HLSDK.Instance.QuickLogin(Action<bool>)` | 빠른 로그인 |
| `HLSDK.Instance.IsAdSupported()` | 광고 지원 여부 |
| `HLSDK.Instance.LoadInterstitialAd(Action<bool>)` | 전면 광고 로드 |
| `HLSDK.Instance.ShowInterstitialAd(start, success, close, fail)` | 전면 광고 노출 |
| `HLSDK.Instance.LoadRewardedAd(Action<bool>)` | 보상형 광고 로드 |
| `HLSDK.Instance.ShowRewardedAd(start, success, close, fail)` | 보상형 광고 노출 |
| `HLSDK.Instance.GetProducts(Action<bool>)` | 상품 목록 조회 |
| `HLSDK.Instance.GetProductInfoByOriginalPID(string)` | 상품 정보 조회 |
| `HLSDK.Instance.PurchaseByOriginalPID(pid, giveCallback, purchaseCallback)` | IAP 구매 |
| `HLSDK.Instance.SubmitLeaderBoard(int, Action<SubmitLeaderBoardResult>?)` | 리더보드 점수 제출 |
| `HLSDK.Instance.OpenLeaderBoard()` | 리더보드 UI 표시 |
| `HLSDK.Instance.GenerateHapticFeedback(string type)` | 햅틱 피드백 |
| `HLSDK.Instance.GetDeviceOS()` | 기기 OS 조회 (`DeviceOS.ANDROID` 등) — 햅틱 타입 등 플랫폼별 분기에 사용 |
| `HLSDK.Instance.ShareLink(string message)` | 공유하기 |
| `HLSDK.Instance.GetSafeAreaTop()` | SafeArea 상단 px |
| `HLSDK.Instance.GetSafeAreaBottom()` | SafeArea 하단 px |
| `HLSDK.Instance.LogDailyLogin()` | 로그인 로그 (세션당 1회, 중복 방지 내장) |
| `await HLSDK.Instance.GetTime()` | 서버 시간 조회 |
| `await HLSDK.Instance.GetUserData()` | 서버 유저 데이터 로드 |
| `await HLSDK.Instance.SetUserData(saveData, timestamp, extraData)` | 서버 유저 데이터 저장 |
| `HLSDK.Instance.GetUserKey()` | UID 조회 |

### NeptuneAPI 직접 접근 (필요 시)

HLSDK wrapper(`HLSDK.Instance.GetTime()` 등)와 `NeptuneAPI.Instance.GetTimeAsync()` 중 프로젝트 관행에 맞는 쪽 사용.
`LogPurchaseAsync`는 SDK 자동 처리 없음 — 구매 성공/실패 콜백 안에서 게임 코드가 직접 호출해야 한다.

---

## 코딩 컨벤션

> **전처리문 규칙**: WebGL 플랫폼 심볼(`WEBGL_TOSS`, `WEBGL_PUREWEB` 등)은 단독 사용 금지.
> 항상 `UNITY_WEBGL`과 조합해야 한다. 이유: `UNITY_WEBGL` 없으면 에디터·Android 빌드에서도 분기가 활성화됨.

**기존 코드 삭제 금지 → 전처리 분기로 묶기**

**패턴 A — `{PLATFORM_SYMBOL}`에만 존재하는 기능** (다른 플랫폼에 대응 없음)

```csharp
#if UNITY_WEBGL && {PLATFORM_SYMBOL}
    // 플랫폼 전용 호출
#endif
```

**패턴 B — 플랫폼마다 다른 구현이 있는 기능** (광고, IAP, 저장/불러오기, 로그인 등) — 기본적으로 이 구조 사용

```csharp
#if UNITY_WEBGL
    #if WEBGL_PUREWEB
        // PureWeb 처리
    #elif WEBGL_TOSS
        // Toss 처리
    #else
        // 미지원 WebGL 플랫폼
    #endif
#else
    // 네이티브(Android/iOS) 처리
#endif
```

작업 계획 수립 단계에서 파악한 기존 분기 현황을 보고 패턴을 선택한다:
- 다른 플랫폼 분기 이미 있음 → 반드시 패턴 B
- WebGL 분기 없고 이 플랫폼 전용 기능 → 패턴 A

> **주의 — 기존 iOS/Android 분기가 나뉜 경우**: `#if !UNITY_WEBGL`로 통으로 감싸면 iOS·Android 로직이 뭉개진다.
> 코드 수정 전 반드시 기존 플랫폼 분기 현황을 확인한다:
> ```bash
> grep -n "UNITY_IOS\|UNITY_ANDROID\|UNITY_STANDALONE\|UNITY_WEBGL" {파일경로}
> ```
>
> | 기존 분기 현황 | 적용 패턴 |
> |---|---|
> | 분기 없음 | `#if !UNITY_WEBGL` 래핑(제거) 또는 `#if UNITY_WEBGL && {PLATFORM_SYMBOL}`(패턴 A/B) |
> | `UNITY_IOS` / `UNITY_ANDROID` 등 이미 나뉨 | 기존 구조 유지 + 맨 앞에 `#if UNITY_WEBGL && {PLATFORM_SYMBOL}` 분기 추가, 기존 분기는 `#elif`로 유지 |
>
> ```csharp
> // ✅ 기존 분기 없음 → !UNITY_WEBGL 래핑(기능 제거인 경우)
> #if !UNITY_WEBGL
>     NativeOnlyLogic();
> #endif
>
> // ✅ 기존에 iOS/Android 분기 있음 → 플랫폼 분기를 맨 앞에 삽입
> #if UNITY_WEBGL && {PLATFORM_SYMBOL}
>     // 플랫폼 처리 (또는 비워두면 해당 기능 비활성화)
> #elif UNITY_IOS
>     IOSLogic();
> #elif UNITY_ANDROID
>     AndroidLogic();
> #endif
>
> // ❌ 잘못된 방법 — 기존 iOS/Android 분기를 !UNITY_WEBGL로 통으로 감싸면
> //    iOS와 Android 로직이 하나의 블록으로 뭉개짐
> ```

> **전처리문 3박자 규칙**: 기능을 WebGL용으로 *교체*할 때는 반드시 `#else`에 원본 코드를 보존한다. 기능을 *제거*할 때는 else 없이 가드만으로 충분하다.
>
> ```csharp
> // ✅ 교체 — #else 필수 (원본 보존)
> #if UNITY_WEBGL && {PLATFORM_SYMBOL}
>     // 플랫폼 처리
> #else
>     NativeMethod();
> #endif
>
> // ✅ 제거 — #else 불필요
> #if !UNITY_WEBGL
>     nativeOnlyButton.SetActive(true);
> #endif
> ```

> **타이밍 이슈 체크리스트** — 코드를 삽입하기 전과 수정한 후 모두 확인한다.
>
> **삽입 전 — 삽입 위치 결정 시:**
> - [ ] 삽입 코드가 참조하는 컴포넌트가 해당 시점에 이미 초기화됐는가? (`Awake` → `Start` 순서)
> - [ ] `OnEnable`/`OnDisable` 타이밍: 오브젝트 active 상태 변경 순서와 호출 순서가 맞는가?
> - [ ] 부모-자식 active 의존: 부모가 비활성 상태면 자식의 `Start`/`Awake`가 지연됨
>
> **수정 후 — 코드 삽입 완료 시:**
> - [ ] 삽입한 코드 블록 안에서 null 참조가 발생할 수 있는 라이프사이클 시점이 없는가?
> - [ ] 씬 전환·오브젝트 파괴 시점에 콜백이 살아있는 경우 처리됐는가?

**DEV 우회 패턴**

```csharp
#if UNITY_WEBGL && {PLATFORM_SYMBOL} && WEBGL_DEV_VER
    onResult?.Invoke(true);
#else
    // 실제 로직
#endif
```

**MonoBehaviour 스텁 패턴 — "script missing" 방지**

`#if`로 MonoBehaviour 클래스 전체를 제거하면 씬/프리팹에 컴포넌트로 붙어 있던 경우 Unity가 "script missing" 경고를 띄운다.

판단 기준:
- 씬/프리팹에 컴포넌트로 붙어 있는 클래스 → `#else` 빈 스텁 추가
- `Instantiate`/`AddComponent`로만 동적 생성되는 클래스 → 스텁 불필요

```csharp
#if !(UNITY_WEBGL && {PLATFORM_SYMBOL})
public class SomeManager : MonoBehaviour
{
    // 기존 로직
}
#else
public class SomeManager : MonoBehaviour { }  // script missing 방지
#endif
```

씬/프리팹 첨부 여부 확인:
```bash
grep -rln "SomeManager" Assets --include="*.unity" --include="*.prefab" 2>/dev/null
```
결과 있으면 스텁 필요, 없으면 생략.

### 에디터 섀도잉 검사 (check-editor-shadow) — 커밋 전 필수

이번 작업에서 수정·추가한 .cs 파일만 검사한다. 원본의 기존 WEBGL 체인은 불변식의 기준선이므로 검사 대상에 넣지 않는다.

`{VERIFY_PLATFORM}`(검사 렌즈) 결정: pureweb-porter는 `WEBGL_PUREWEB`, toss-porter는 `WEBGL_TOSS`, platform-porter는 `WEBGL_TOSS`(비-퓨어웹 대표값). **코드 작성용 `{PLATFORM_SYMBOL}`과는 별개 축이다** — 예: platform-porter는 코드엔 `UNITY_WEBGL` 단독을 쓰지만(심볼 없음) 검사 렌즈는 `WEBGL_TOSS`다. `--platform` 인자를 생략하지 않는다.

> **`.porting-context`를 `--platform`에 쓰지 않는다** — 그 파일은 "지금 컴파일할 대상"이고 `--platform`은 "어떤 렌즈로 검사할지"라 축이 다르다. 특히 platform-porter의 산출물은 항상 비-퓨어웹 경로(`#if UNITY_WEBGL && !WEBGL_PUREWEB` 등)에 들어가는데, 파이프라인상 `.porting-context`엔 직전 pureweb-porter가 쓴 `PUREWEB`이 남아 있다. 퓨어웹 렌즈로 검사하면 그 블록들이 "퓨어웹 빌드에서 꺼진 코드"로 판정돼 검사에서 통째로 빠진다(실측: 같은 파일에서 TOSS 렌즈 2건 검출 → PUREWEB 렌즈 1건 누락).

```bash
git status --porcelain -- '*.cs' | awk '{print "--files " $2}' \
  | xargs python3 $H5PW_ROOT/templates/scripts/h5-port-verify.py \
      --platform {VERIFY_PLATFORM} --mode check-editor-shadow
```

| 출력 | 대응 |
|---|---|
| `EDITOR_SHADOWED` | 지목된 분기 조건에 `&& !UNITY_EDITOR` 추가 후 재검사 (exit 1 — 통과 전 커밋 금지) |
| `EVAL_FAILED` | 해당 라인을 Read로 직접 확인해 섀도잉 여부를 수동 판정 |
| `✅ 섀도잉 없음` | 커밋 진행 |

> STEP 4 최종 검증(`h5-port-verify.py --mode verify`)의 `❌`/`⚠️` 결과 처리(verify-exceptions.json 절차)는 `porting-verify` 스킬이 전담한다 — 여기서 다루지 않는다.

---

<!-- ======================================================
     여기서부터 포터 전용 내용 작성
     - 플랫폼 정의
     - 진입점 (NATIVE_BASELINE.md + pureweb-checklist.md 읽기)
     - 의존성 파악 및 병렬 작업 계획
     - 작업 순서
     - 검증
     - 완료 후 채팅 출력
     ====================================================== -->
