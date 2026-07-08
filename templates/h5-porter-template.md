---
name: {PORTER_NAME}
description: {PORTER_DESCRIPTION}
tools: Read, Bash, Edit, Write, Agent
---

# {PORTER_TITLE} 에이전트

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
>
> grep을 **첫 번째** 수단으로 쓰지 않는다. VOCAB에 없을 때만 쓴다.
>
> **VOCAB 업데이트 원칙**: grep fallback으로 발견한 파일:라인은 작업 완료 후 `Docs/porting/PORTING_VOCAB.md` `## 포터 기록` 섹션에 추가한다.

---

## 컴파일 체크 자동화

`.cs` 파일 수정 시 PostToolUse hook이 자동으로 컴파일을 검사한다. hook 출력 신호에 즉시 반응한다:

| 신호 | 대응 |
|---|---|
| `✅ [COMPILE_OK]` | 다음 단계 계속 진행 |
| `❌ [COMPILE_ERROR]` | 에러 즉시 수정 → 수정 파일 저장 시 자동 재검사 |
| `⚠️ [COMPILE_REQUIRED]` | **즉시 중단** — 아래 처리 |

`⚠️ [COMPILE_REQUIRED]` 발생 시:

1. 표준 스크립트로 실행 (사전 점검·부수효과 되돌리기 내장):
   ```bash
   PLATFORM=$(cat .porting-context 2>/dev/null || echo {PLATFORM_SYMBOL})
   bash ~/github/h5-porting-workflow/templates/scripts/compile-check.sh "$PLATFORM"
   ```
2. 출력 판정: `✅` → 계속 / `❌` → 에러 수정 후 재실행 / `⛔ STOP`(에디터 열림) → AskUserQuestion: "컴파일 체크를 위해 Unity를 닫아주세요. 닫으셨나요?" — 닫음 → 재실행 / 아직 열려있음 → 닫은 후 알려달라고 안내. 그 전까지 `.cs` 수정 없이 대기.

> hook 미설정 시 → Unity 메뉴 **Tools/H5/Compile Check ({PLATFORM_SYMBOL})** 수동 실행

> 각 단계의 담당 표시:
> - 🤖 **AI 자동** — grep 탐색 + 코드 수정까지 진행
> - ❓ **판단 필요** — AI가 탐색 후 AskUserQuestion으로 사용자 결정
> - 👤 **사람 결정** — AI는 현황만 리포트, 결정·실행은 사람

---

## worktree 병렬 작업 방침

수정 대상 파일이 겹치지 않는 태스크 그룹은 worktree로 병렬 실행한다.

- **파일 겹침 없음** → worktree로 병렬 실행
- **파일 겹침 있음** → 순차 처리 (같은 worktree)

```bash
# worktree 생성
git worktree add ../{이름} -b {브랜치명}

# 태스크 완료 후 merge, 제거
git worktree remove ../{이름}
```

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

> **플랫폼 에이전트 전용** — PureWeb 등 비플랫폼 포터는 이 섹션을 제거한다.

SDK 위치: `Assets/HyperLane/` — **직접 수정 금지**

### HLSDK 접근

```csharp
HLSDK.Instance                                     // 싱글톤, 자동 생성
await HLSDK.Instance.Initialize();                 // 앱 시작 시 1회 필수
HLSDK.Instance.Provider                            // WebGLProviderHandler (WEBGL_TOSS → TossHandler)
var toss = HLSDK.Instance.Provider as TossHandler; // 배너·Managed 프로모션 전용
```

### 주요 이벤트

```csharp
// "1" = 백그라운드, "0" = 포그라운드
HLSDK.Instance.OnApplicationPause += (string pauseStr) => { };
```

### 주요 API

| 메서드 | 용도 |
|---|---|
| `HLSDK.Instance.Login(Action<bool>)` | Toss 로그인 |
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
| `HLSDK.Instance.ShareLink(string message)` | 공유하기 |
| `HLSDK.Instance.GetSafeAreaTop()` | SafeArea 상단 px |
| `HLSDK.Instance.GetSafeAreaBottom()` | SafeArea 하단 px |
| `HLSDK.Instance.LogDailyLogin()` | 로그인 로그 (세션당 1회, 중복 방지 내장) |
| `await HLSDK.Instance.GetTime()` | 서버 시간 조회 |
| `await HLSDK.Instance.GetUserData()` | 서버 유저 데이터 로드 |
| `await HLSDK.Instance.SetUserData(saveData, timestamp, extraData)` | 서버 유저 데이터 저장 |

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
> 기존에 `UNITY_IOS` / `UNITY_ANDROID` 분기가 있으면 `#if UNITY_WEBGL && {PLATFORM_SYMBOL}`를 맨 앞에 삽입하고 기존 분기를 `#elif`로 유지한다:
>
> ```csharp
> #if UNITY_WEBGL && {PLATFORM_SYMBOL}
>     // 플랫폼 처리
> #elif UNITY_IOS
>     IOSLogic();
> #elif UNITY_ANDROID
>     AndroidLogic();
> #endif
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

> **타이밍 이슈 주의**: 콘텐츠 코드 수정 시 삽입 위치 결정 전 Unity 라이프사이클 의존성을 확인한다.
> - `Awake`/`Start` 순서: 삽입 코드가 참조하는 컴포넌트가 이미 초기화됐는지 확인
> - `OnEnable`/`OnDisable`: 오브젝트 active 상태 변경 순서와 호출 타이밍이 맞는지 확인
> - 부모-자식 active 의존: 부모가 비활성 상태면 자식의 `Start`/`Awake`가 지연됨

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
#if !{PLATFORM_SYMBOL}
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
