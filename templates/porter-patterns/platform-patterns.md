# platform-porter 코드 패턴 참고 문서

> platform-porter.md의 각 스텝에서 참조한다. 이 파일 단독으로는 읽지 않는다.

## 2. 서버 시간 체크

```csharp
#if UNITY_WEBGL
    UniTask<NTH5Response<GetTimeResponse>> task = HLSDK.Instance.GetTime();
    UniTask<NTH5Response<GetTimeResponse>>.Awaiter awaiter = task.GetAwaiter();
    yield return new WaitUntil(() => awaiter.IsCompleted);

    DateTime standardTime = DateTime.UtcNow;
    NTH5Response<GetTimeResponse> response = awaiter.GetResult();
    if (response.success && response.data != null)
    {
        DateTime dt;
        if (DateTime.TryParse(response.data.utc, null,
            System.Globalization.DateTimeStyles.AdjustToUniversal, out dt))
            standardTime = dt;
    }
    /* 프로젝트의 서버 시간 설정 함수 호출 */
#else
    // 기존 외부 HTTP API 로직
#endif
```

## 3. 로그인 API 연동

**삽입 패턴:**

```csharp
#if UNITY_WEBGL
bool? loginResult = null;
HLSDK.Instance.QuickLogin(loginOk => loginResult = loginOk);

// WaitUntil은 Unity 기본 제공 (UnityEngine.WaitUntil)
yield return new WaitUntil(() => loginResult.HasValue);
if (loginResult != true) yield break;
// UniTask 사용 프로젝트: await UniTask.WaitUntil(() => loginResult.HasValue); if (loginResult != true) return;
#endif
// 이후 LoadCloud 등 데이터 로드
```

**Coroutine 패턴** (`Initialize()` 없음 케이스 — 있으면 `InitPlatform()` 관련 부분만 발췌 적용):

```csharp
private IEnumerator {GAME_INIT_METHOD}()
{
#if UNITY_WEBGL
    yield return HLSDK.Instance.Initialize().ToCoroutine();
#if WEBGL_DEBUG_CONSOLE
    RegisterCheats();
#endif
    yield return StartCoroutine(InitPlatform());
    if (!_platformLoginSuccess) yield break; // 로그인 실패 — 이후 데이터 로드 등 기존 로직 진행 금지
#endif
    // 기존 로직 계속
}

#if UNITY_WEBGL
private bool _platformLoginSuccess;

private IEnumerator InitPlatform()
{
    bool? loginResult = null;
    HLSDK.Instance.QuickLogin(loginOk => loginResult = loginOk);
    yield return new WaitUntil(() => loginResult.HasValue);
    _platformLoginSuccess = loginResult == true;
    if (!_platformLoginSuccess) yield break;

    // GetProducts, LoadCloud 등
}
#endif
```

**UniTask 패턴** (`Initialize()` 없음 케이스 — 있으면 `InitPlatform()` 관련 부분만 발췌 적용):

```csharp
private async UniTask {GAME_INIT_METHOD}()
{
#if UNITY_WEBGL
    await HLSDK.Instance.Initialize();
#if WEBGL_DEBUG_CONSOLE
    RegisterCheats();
#endif
    bool platformLoginSuccess = await InitPlatform();
    if (!platformLoginSuccess) return; // 로그인 실패 — 이후 데이터 로드 등 기존 로직 진행 금지
#endif
    // 기존 로직 계속
}

#if UNITY_WEBGL
private async UniTask<bool> InitPlatform()
{
    bool? loginResult = null;
    HLSDK.Instance.QuickLogin(loginOk => loginResult = loginOk);
    await UniTask.WaitUntil(() => loginResult.HasValue);
    if (loginResult != true) return false;

    // GetProducts, LoadCloud 등
    return true;
}
#endif
```

## 3-A. 로그인 로그 삽입

기존 분기 없는 경우의 기본형(패턴 B 계층 구조 — 코딩 컨벤션 참조). 실제 삽입 위치에 이미 `#if UNITY_WEBGL { ... }` 등 다른 계층이 있으면 그 구조에 맞춰 끼워 넣는다(플랫 `&&` 조건으로 새로 쓰지 않는다).

```csharp
// 로비 진입 완료 시점 (Start, OnEnable, 초기화 콜백 등)
#if UNITY_WEBGL
    #if WEBGL_PUREWEB
        // PureWeb — 제외
    #else
        #if !UNITY_EDITOR
        HLSDK.Instance.LogDailyLogin();
        #endif
    #endif
#endif
```

## 4. 백그라운드 사운드 처리

```csharp
#if UNITY_WEBGL
HLSDK.Instance.OnApplicationPause += (string pauseStr) =>
{
    bool isPause = pauseStr == "1";
    AudioListener.pause = isPause;
    AudioListener.volume = isPause ? 0f : 1f;
};
#endif
```

## 5-2. 보상형 / 전면 광고 API

```csharp
#if UNITY_WEBGL && WEBGL_PUREWEB
    isLoadedRewardVideo = true;
#elif UNITY_WEBGL
    HLSDK.Instance.LoadRewardedAd(success => { isLoadedRewardVideo = success; });
#else
    // 기존 네이티브 로직 — 유지
#endif
```

**보상형 광고 패턴:**

```csharp
void LoadRewardVideo()
{
#if UNITY_WEBGL
    HLSDK.Instance.LoadRewardedAd(success => { isLoadedRewardVideo = success; });
#else
    isLoadedRewardVideo = true;
#endif
}

void ShowRewardVideo(/* 보상 콜백, 미보상 콜백 */)
{
#if UNITY_WEBGL
    HLSDK.Instance.ShowRewardedAd(
        startCall: () =>
        {
            OnAdVisibilityChanged(true);
        },
        successCall: () =>
        {
            /* 보상 지급 */
            /* 보상 콜백 호출 */
        },
        closeCall: (bool rewarded) =>
        {
            OnAdVisibilityChanged(false);
            if (!rewarded) /* 미보상 콜백 호출 */;
        },
        failCall: (bool canceled) =>
        {
            OnAdVisibilityChanged(false);
            /* 실패/취소 콜백 호출 */
        }
    );
#endif
}
```

**전면 광고 패턴:**

```csharp
void LoadInterstitial()
{
#if UNITY_WEBGL
    HLSDK.Instance.LoadInterstitialAd(success => { isLoadedInterstitial = success; });
#else
    isLoadedInterstitial = true;
#endif
}

void ShowInterstitial(/* 종료 콜백 */)
{
#if UNITY_WEBGL
    HLSDK.Instance.ShowInterstitialAd(
        startCall: () => { OnAdVisibilityChanged(true); },
        successCall: () => { /* 클릭 이벤트 등 */ },
        closeCall: () => { OnAdVisibilityChanged(false); /* 종료 콜백 */ },
        failCall: () => { OnAdVisibilityChanged(false); /* 실패 이벤트 */ }
    );
#endif
}
```

**전면 광고 pre-load:**

```csharp
// 필드 (클래스 상단)
private bool _interstitialAdLoaded = false;
private bool _isLoadingInterstitial = false;
private System.Action _pendingShowInterstitial = null;

private void LoadInterstitialAd()
{
#if UNITY_WEBGL
    if (_isLoadingInterstitial) return;
    _isLoadingInterstitial = true;
    HLSDK.Instance.LoadInterstitialAd(ok =>
    {
        _isLoadingInterstitial = false;
        _interstitialAdLoaded = ok;
        if (!ok) { _pendingShowInterstitial = null; return; }
        if (_pendingShowInterstitial == null) return;
        System.Action pending = _pendingShowInterstitial;
        _pendingShowInterstitial = null;
        pending();
    });
#endif
}

public void ShowInterstitial()
{
#if UNITY_WEBGL
    if (!_interstitialAdLoaded)
    {
        _pendingShowInterstitial = ShowInterstitialInternal;
        LoadInterstitialAd();
        return;
    }
    ShowInterstitialInternal();
#else
    // 기존 네이티브 로직
#endif
}

private void ShowInterstitialInternal()
{
    _interstitialAdLoaded = false;
    OnAdVisibilityChanged(true);
    HLSDK.Instance.ShowInterstitialAd(
        startCall: () => { },
        successCall: () => { },
        closeCall: () => { OnAdVisibilityChanged(false); LoadInterstitialAd(); },
        failCall: () => { OnAdVisibilityChanged(false); }
    );
}
```

**보상형 광고 pre-load:**

```csharp
// 필드 (클래스 상단)
private bool _rewardedAdLoaded = false;
private bool _isLoadingRewardedAd = false;
private System.Action _pendingShowRewarded = null;

private void LoadRewardedAd()
{
#if UNITY_WEBGL
    if (_isLoadingRewardedAd) return;
    _isLoadingRewardedAd = true;
    HLSDK.Instance.LoadRewardedAd(ok =>
    {
        _isLoadingRewardedAd = false;
        _rewardedAdLoaded = ok;
        if (!ok) { _pendingShowRewarded = null; return; }
        if (_pendingShowRewarded == null) return;
        System.Action pending = _pendingShowRewarded;
        _pendingShowRewarded = null;
        pending();
    });
#endif
}

public void ShowRewardedAd(/* 보상 콜백, 미보상 콜백 */)
{
#if UNITY_WEBGL
    if (!_rewardedAdLoaded)
    {
        _pendingShowRewarded = () => ShowRewardedAdInternal(/* 콜백 전달 */);
        LoadRewardedAd();
        return;
    }
    ShowRewardedAdInternal(/* 콜백 전달 */);
#else
    // 기존 네이티브 로직
#endif
}

private void ShowRewardedAdInternal(/* 보상 콜백, 미보상 콜백 */)
{
    _rewardedAdLoaded = false;
    OnAdVisibilityChanged(true);
    HLSDK.Instance.ShowRewardedAd(
        startCall: () => { },
        successCall: () => { /* 보상 지급 */ },
        closeCall: (bool rewarded) =>
        {
            OnAdVisibilityChanged(false);
            if (!rewarded) { /* 미보상 콜백 */ }
            LoadRewardedAd();
        },
        failCall: (bool canceled) => { OnAdVisibilityChanged(false); }
    );
}
```

## 5-3. 광고 중 BGM / 게임 중지 처리

**A 패턴 — 게임중지: 불필요 (BGM 처리만)**

광고 매니저 클래스에 추가:

```csharp
private void OnAdVisibilityChanged(bool isVisible)
{
    AudioListener.pause = isVisible;
    AudioListener.volume = isVisible ? 0f : 1f;
}
```

**B 패턴 — 게임중지: 필요 (BGM + TimeScale + Coroutine 타이머)**

**1단계 — 광고 매니저 클래스 수정**

필드 선언 (클래스 상단):

```csharp
private bool _adPaused = false;
private float _savedTimeScale = 1f;

// Coroutine 타이머 컴포넌트가 광고 상태를 감지하기 위한 static 이벤트
public static event System.Action<bool> OnAdVisibilityChangedEvent;
```

`OnAdVisibilityChanged` 구현:

```csharp
private void OnAdVisibilityChanged(bool isVisible)
{
    AudioListener.pause = isVisible;
    AudioListener.volume = isVisible ? 0f : 1f;

    if (isVisible)
    {
        if (!_adPaused)
        {
            _savedTimeScale = Time.timeScale;
            _adPaused = true;
        }
        Time.timeScale = 0f;
    }
    else
    {
        _adPaused = false;
        Time.timeScale = _savedTimeScale;
    }

    OnAdVisibilityChangedEvent?.Invoke(isVisible);
}
```

**패턴 Y — `WaitForSecondsRealtime` / `unscaledDeltaTime` / `Stopwatch` 기반 타이머가 있는 경우**

`Time.timeScale = 0`에 영향받지 않으므로 `OnAdVisibilityChangedEvent` 구독 패턴 추가:

```csharp
// Coroutine 타이머 컴포넌트에서
private bool _adPaused = false;

private void OnEnable()
{
    AdManager.OnAdVisibilityChangedEvent += OnAdPauseChanged;
}

private void OnDisable()
{
    AdManager.OnAdVisibilityChangedEvent -= OnAdPauseChanged;
}

private void OnAdPauseChanged(bool isVisible)
{
    _adPaused = isVisible;
}

// 기존 Realtime 타이머 루프 앞에 WaitUntil 삽입
private IEnumerator CountdownCoroutine()
{
    while (count > 0)
    {
        yield return new WaitUntil(() => !_adPaused); // 광고 중 대기
        yield return new WaitForSecondsRealtime(1f);
        count--;
    }
}
```

각 광고 콜백에서 호출 (5-2 패턴에 이미 적용되어 있음):

```csharp
startCall: () => { OnAdVisibilityChanged(true); },
closeCall: () => { OnAdVisibilityChanged(false); /* 후처리 */ },
failCall: () => { OnAdVisibilityChanged(false); }
```

## 6-1. 가격 가져오기

```csharp
var productsDone = false;
HLSDK.Instance.GetProducts(ok => { productsDone = true; });
yield return new WaitUntil(() => productsDone);
```

## 6-2. 가격 UI 표시

```csharp
// {PRICE_UI_CLASS} — 범용 메서드 추가 (전처리 없이)
public void SetPrice(string priceText)
{
    priceLabel.text = priceText;
}

// 호출부 — WebGL 빌드에서만
#if UNITY_WEBGL
var info = HLSDK.Instance.GetProductInfoByOriginalPID(originalPid);
priceUI.SetPrice(info.displayAmount);
#endif
```

## 6-3. 구매 연동

```csharp
public void {IAP_METHOD}(string productId, Action OnSuccess, Action OnFailed = null)
{
#if UNITY_EDITOR
    OnSuccess?.Invoke();
    return;
#elif WEBGL_PUREWEB
    GiveProduct(productId);  // HLSDK 미경유
    OnSuccess?.Invoke();
#elif UNITY_WEBGL
    HLSDK.Instance.PurchaseByOriginalPID(
        productId,
        giveProductInfo =>
        {
            OnSuccess?.Invoke();
        },
        purchaseResult =>
        {
            if (!purchaseResult.success)
            {
        #if WEBGL_DEV_VER
                OnSuccess?.Invoke(); // DEV: 실패/뒤로가기도 강제 지급 (플랫폼 전용 정책이면 개별 포터가 재확인)
        #else
                OnFailed?.Invoke();
        #endif
            }
        }
    );
#else
    // 기존 네이티브 IAP 로직
#endif
}
```

## 7-0. 치트 — 서버/로컬 초기화

```csharp
#if WEBGL_DEBUG_CONSOLE
    RegisterCheats();
#endif
```

```csharp
void RegisterCheats()
{
    CheatRegister.ClearAll();

    // DEV/LIVE 키는 리터럴로 직접 참조한다 — SAVE_KEY 상수는 빌드 시점에
    // 둘 중 하나로만 고정되므로(8-A 패턴), 지금 빌드가 아닌 쪽 키를 지우려면
    // 상수가 아니라 두 리터럴 문자열이 둘 다 필요하다.
    const string SAVE_KEY_DEV = "{GameName}_Data_DEV";
    const string SAVE_KEY_LIVE = "{GameName}_Data_LIVE";

    CheatRegister.Register(
        "Reset Local (DEV)",
        "Reset local data for DEV build",
        Color.yellow,
        () => ResetLocal(SAVE_KEY_DEV)
    );

    CheatRegister.Register(
        "Reset Local+Server (DEV)",
        "Reset local and server data for DEV build",
        Color.red,
#if !UNITY_EDITOR
        () =>
        {
            ResetLocal(SAVE_KEY_DEV);
            ResetServerAsync(SAVE_KEY_DEV).Forget();
        }
#else
        () => ResetLocal(SAVE_KEY_DEV)
#endif
    );

    CheatRegister.Register(
        "Reset Local (LIVE)",
        "Reset local data for LIVE build",
        Color.yellow,
        () => ResetLocal(SAVE_KEY_LIVE)
    );

    CheatRegister.Register(
        "Reset Local+Server (LIVE)",
        "Reset local and server data for LIVE build. Temporary/on-demand tool — use only when actually needed.",
        Color.red,
        () =>
        {
            ResetLocal(SAVE_KEY_LIVE);
            ResetServerAsync(SAVE_KEY_LIVE).Forget();
        }
    );

    CheatRegister.Build(); // 반드시 마지막에 호출 — 미호출 시 UI에 표시 안 됨
}

async UniTaskVoid ResetServerAsync(string key)
{
    string empty = /* 검수받은 빈 데이터 직렬화 */;
    string timestamp = new System.DateTimeOffset(System.DateTime.UtcNow).ToUnixTimeSeconds().ToString();
    NTH5Response<SetUserDataResponse> result = await HLSDK.Instance.SetUserData(empty, timestamp, "");
    Debug.Log($"[CHEAT] {key} server reset: " + (result.success ? "success" : "failed - " + result.error));
}

// 게임 정지(재시작 전 자동 저장 등이 덮어쓰는 것 방지) + VOCAB 저장 방식에 따른 실제 로컬 삭제
void ResetLocal(string key)
{
    Time.timeScale = 0f;
    // VOCAB 저장 방식에 따른 로컬 초기화 코드 — key 대상
}
```

## 7. 서버 저장 / 불러오기 — HLSDK 연동

```csharp
#if UNITY_WEBGL
    string allData = {LOCAL_SAVE_METHOD}(); // Base64 인코딩 포함 — 그대로 재사용
    #if WEBGL_PUREWEB
    #else
    // 이 지점은 !WEBGL_PUREWEB 확정 — allData 재사용해 서버 동기화만 수행
    string extraData = /* "key1 : val1, key2 : val2" — 서버 모니터링용 필드 */;
    string timestamp = new System.DateTimeOffset(/* 프로젝트의 현재 시각 소스 — 예: System.DateTime.UtcNow */).ToUnixTimeSeconds().ToString();

    HLSDK.Instance.SetUserData(allData, timestamp, extraData)
        .ContinueWith((NTH5Response<SetUserDataResponse> result) =>
        {
            if (result.success) Debug.Log("[HLSDK] SAVE OK");
            else Debug.Log("[HLSDK] SAVE FAIL: " + result.error);
        }).Forget();

    if (callback != null) callback(/* 기존 성공 결과 코드 — 예: RESULT_CODE.SUCCESS */);
    #endif
#else
    // 기존 네이티브 로직 (유지)
#endif
```

**"없음" 케이스 — 전체 신규 작성 (같은 계층 구조를 이 포터가 직접 만든다):**

```csharp
public static void {SAVE_METHOD}(/* 기존 메서드의 콜백 시그니처를 그대로 유지 */ callback)
{
#if UNITY_WEBGL
    #if WEBGL_PUREWEB
    // 퓨어웹은 로컬만 — HLSDK 서버 동기화 없음
    #else
    string allData;
    try
    {
        allData = /* {데이터 형식}으로 직렬화 후 Base64 인코딩 */;
    }
    catch (System.Exception e)
    {
        Debug.LogError($"[Save] 직렬화/Base64 인코딩 실패: {e.Message}");
        if (callback != null) callback(/* 기존 실패 결과 코드 */);
        return;
    }

    {LOCAL_SAVE_METHOD}();

    string extraData = /* 서버 모니터링용 필드 */;
    string timestamp = new System.DateTimeOffset(/* 현재 시각 소스 */).ToUnixTimeSeconds().ToString();

    HLSDK.Instance.SetUserData(allData, timestamp, extraData)
        .ContinueWith((NTH5Response<SetUserDataResponse> result) =>
        {
            if (result.success) Debug.Log("[HLSDK] SAVE OK");
            else Debug.Log("[HLSDK] SAVE FAIL: " + result.error);
        }).Forget();

    if (callback != null) callback(/* 기존 성공 결과 코드 */);
    #endif
#else
    // 기존 CloudOnce 로직 (보존)
#endif
}
```

```csharp
public static async UniTask {LOAD_METHOD}(/* 기존 메서드의 콜백 시그니처를 그대로 유지 */ callback)
{
#if !UNITY_WEBGL
    // 기존 CloudOnce 로직 (보존)
#elif UNITY_WEBGL
    #if !WEBGL_PUREWEB
    // 서버에서 불러와 로컬보다 최신이면 "로컬 저장소"에 덮어쓴다 — 퓨어웹 제외
    NTH5Response<GetUserDataResponse> ret = await HLSDK.Instance.GetUserData();
    if (ret.success && ret.data != null)
    {
        string svrData = ret.data.userData;
        if (!string.IsNullOrEmpty(svrData))
        {
            try
            {
                // Base64 디코딩 (저장 시 인코딩했으므로 복원 필요). 형식이 바이너리면 byte[]로 받아 역직렬화.
                string svrJson = System.Text.Encoding.UTF8.GetString(System.Convert.FromBase64String(svrData));

                // 단조 증가 값(플레이 횟수 등)으로 서버/로컬 최신 판별
                // 타임스탬프 사용 금지 — 기기 시간 신뢰 불가
                int svrCount = /* svrJson에서 판별 기준 필드 역직렬화 */;
                int localCount = /* 로컬 판별 기준 값 */;
                if (svrCount > localCount)
                    /* svrJson을 역직렬화해 "로컬 저장소"에 덮어쓰기 ({LOCAL_SAVE_METHOD} 등).
                       게임 메모리에 직접 적용 금지 — 아래 {LOCAL_LOAD_METHOD}()가 덮어쓴다. */;
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[Load] 서버 데이터 디코딩 실패 — 손상된 데이터로 간주, 로컬 데이터 유지: {e.Message}");
            }
        }
    }
    #endif

    {LOCAL_LOAD_METHOD}(); // 로컬 불러오기 — VOCAB에서 확인한 실제 함수명 사용
    // 위에서 서버 데이터를 로컬 저장소에 기록했으므로, 여기서 읽으면 서버 최신값이 게임에 반영된다.
    if (callback != null) callback(/* 기존 성공 결과 코드 — 예: RESULT_CODE.SUCCESS */);
#endif
}
```

## 8. 햅틱

기존 `Vibrate()` 호출 위치에 `#if UNITY_WEBGL` 분기 추가:

```csharp
#if UNITY_WEBGL
    HapticController.Generate(HapticTier.Tap); // Tier는 기존 세기 표현·기획 명세 참조
#else
    // 기존 진동 로직
#endif
```

네이티브 진동을 직접 호출하는 유틸 함수가 있으면 내부에 가드 추가:

```csharp
public static void Vibrate()
{
#if UNITY_WEBGL
    HapticController.Generate(HapticTier.Tap);
    return;
#endif
    // 기존 네이티브 진동 호출 — 예: SomeNative.Vibrate()
}
```

## 10-1. 랭킹 접근 버튼 확인

버튼 활성화 분기 — 리더보드 미지원 플랫폼(현재 Kakao/PureWeb)은 숨긴다:

```csharp
void Start()
{
#if UNITY_WEBGL
    gameObject.SetActive(true);
#else
    gameObject.SetActive(false);
#endif
}
```

## 10-2. 랭킹 보드 연동

`OpenLeaderBoard()` 호출이 없으면 랭킹 버튼 클릭 핸들러에 삽입.

```csharp
#if UNITY_WEBGL
    HLSDK.Instance.OpenLeaderBoard();
#else
    // 기존 리더보드 UI
#endif
```

## 10-3. 랭킹 점수 등록 코드

`UNITY_WEBGL` 분기 없는 제출 호출에 분기 추가:

```csharp
#if UNITY_WEBGL && WEBGL_LIVE_VER
    HLSDK.Instance.SubmitLeaderBoard(score);
#else
    // 기존 CloudOnce 등 리더보드 제출 (보존)
#endif
```

## 11. 공유하기

`#if UNITY_WEBGL` 분기를 기존 함수 내부에 추가:

```csharp
public void OnClickShare()
{
#if UNITY_WEBGL
    HLSDK.Instance.ShareLink("공유 문구"); // TODO: 기획 확정 후 교체
#else
    // 기존 NativeShare 등
#endif
}
```

## 13. UID / version 추가

`GetUserKey()`는 HLSDK 공통 API다(퓨어웹에서도 동작).

```csharp
#if UNITY_WEBGL
    uidText.text = HLSDK.Instance.GetUserKey();
    versionText.text = Application.version;
#endif
```

## 14. 불필요한 UI 삭제

**비활성화 처리 🤖**

결정된 항목의 파일을 Read해서 버튼 초기화 또는 표시 로직을 `#if !UNITY_WEBGL`로 감싼다:

```csharp
#if !UNITY_WEBGL
    restoreButton.SetActive(true);
    contactUsButton.SetActive(true);
#endif
```

