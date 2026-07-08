# pureweb-porter 코드 패턴 참고 문서

> pureweb-porter.md의 각 스텝에서 참조한다. 이 파일 단독으로는 읽지 않는다.

## 0. SDK 초기화

**Coroutine 패턴** (로그인 단계와 동일하게 `bool?`/`WaitUntil` 구조로 통일):

```csharp
private IEnumerator {GAME_INIT_METHOD}()
{
#if UNITY_WEBGL
    bool? sdkInitSuccess = null;
    InitializeSdk(success => sdkInitSuccess = success).Forget();
    yield return new WaitUntil(() => sdkInitSuccess.HasValue);
    if (sdkInitSuccess != true) yield break; // 초기화 실패 — 이후 로직 진행 금지

#if WEBGL_DEBUG_CONSOLE
    RegisterCheats();
#endif
    // platform-porter가 여기 이어서 로그인(InitPlatform()) 호출을 삽입한다
#endif
    // 기존 로직 계속
}

#if UNITY_WEBGL
private async UniTask InitializeSdk(System.Action<bool> onComplete)
{
    try
    {
        await HLSDK.Instance.Initialize();
        onComplete?.Invoke(true);
    }
    catch (System.Exception e)
    {
        Debug.LogError($"[SDK] 초기화 실패: {e.Message}");
        onComplete?.Invoke(false);
    }
}
#endif
```

**UniTask 패턴:**

```csharp
private async UniTask {GAME_INIT_METHOD}()
{
#if UNITY_WEBGL
    bool sdkInitSuccess = true;
    try
    {
        await HLSDK.Instance.Initialize();
    }
    catch (System.Exception e)
    {
        Debug.LogError($"[SDK] 초기화 실패: {e.Message}");
        sdkInitSuccess = false;
    }
    if (!sdkInitSuccess) return; // 초기화 실패 — 이후 로직 진행 금지

#if WEBGL_DEBUG_CONSOLE
    RegisterCheats();
#endif
    // platform-porter가 여기 이어서 로그인(InitPlatform()) 호출을 삽입한다
#endif
    // 기존 로직 계속
}
```

## 1-A. 리뷰 팝업 제거

```csharp
#if !UNITY_WEBGL
    // 결정된 범위에 따라 감싸기
#endif
```

## 2. SafeArea 제거

```csharp
#if !UNITY_WEBGL
    ApplySafeArea();
#endif
```

## 3. Screen.fullScreen / SetResolution 방지

```csharp
#if UNITY_WEBGL
Screen.SetResolution(width, height, false);
#else
Screen.SetResolution(width, height, true);
#endif
```

## 3-B. 외부 네트워크 요청 차단

```csharp
// UnityWebRequest 차단 예시 (서버 시간)
public void GetServerTime(Action<DateTime> callback)
{
#if UNITY_WEBGL
    callback?.Invoke(DateTime.UtcNow); // platform-porter에서 HLSDK.Instance.GetTime()으로 세분화됨
#else
    // 기존 UnityWebRequest 로직
#endif
}

// Application.OpenURL 차단
#if !UNITY_WEBGL
    Application.OpenURL(url);
#endif
```

## 5. 광고 즉시 지급

**해결 방법 (예시 — 실제 메서드 시그니처는 코드에서 확인):**

```csharp
// 예시
public void ShowRewardAD(AdRewardType type, GameObject context, System.Action<bool> OnSuccess)
{
#if UNITY_WEBGL && WEBGL_PUREWEB
    OnSuccess?.Invoke(true);
    return;
#else
    // 기존 광고 로직 — 나중에 platform-porter가 이 #else 앞에 #elif UNITY_WEBGL(HLSDK 경유)을 끼워넣는다
#endif
}
```

## 6. IAP 즉시 지급

**해결 방법 (예시 — 실제 메서드 시그니처는 코드에서 확인, `infiniteranch-h5-client` IAPManager.cs:280-301 선례와 동일 스타일):**

```csharp
// 예시
public void Purchase(string productId)
{
#if UNITY_WEBGL && WEBGL_PUREWEB
    GiveProduct(productId);
    return;
#else
    // 기존 IAP 로직 — 나중에 platform-porter가 이 #else 앞에 #elif UNITY_WEBGL(HLSDK 경유)을 끼워넣는다
#endif
}
```

## 7-0. 사전 체크 — MonoBehaviour 씬/프리팹 첨부 여부

```csharp
// ✅ 씬/프리팹 첨부 있음 — 클래스 유지, 내부만 가드
using UnityEngine;
#if UNITY_ANDROID || UNITY_IOS
using SomeSDK;
#endif

public class SomeManager : MonoBehaviour
{
    public static SomeManager instance;

#if UNITY_ANDROID || UNITY_IOS
    // 전체 구현
    private void Awake() { instance = this; /* SDK 초기화 */ }
    // ... 나머지 멤버
#else
    private void Awake() { instance = this; }
#endif
}

// ✅ 씬/프리팹 첨부 없음 — 클래스 전체 래핑 허용
#if !UNITY_WEBGL
public class SomeManager : MonoBehaviour { ... }
#endif
```

## 7-3. C# 코드 가드

```csharp
#if !UNITY_WEBGL
using SomeSDK;
#endif
```

## 7-5. WebGL 비호환 서비스 클래스 — 메서드 레벨 분기

```csharp
// ❌ 잘못된 방법
#if !UNITY_WEBGL
public class TimeServer { ... }
#endif

// ✅ 올바른 방법 — 메서드 단위 분기 + WebGL 스텁
public class TimeServer
{
    public void GetServerTime(Action<DateTime> callback)
    {
#if UNITY_WEBGL
        // TODO: NeptuneAPI 등으로 교체
        callback?.Invoke(DateTime.UtcNow);
#else
        // 기존 TcpClient + Thread 코드
#endif
    }
}
```

## 8. 서버 저장 차단 / LocalStorage 검증

```csharp
// 예시
public void SaveToServer(string key, string value, System.Action<bool> onComplete)
{
#if UNITY_WEBGL
    string allData = {LOCAL_SAVE_METHOD}(); // Base64 인코딩된 문자열 반환 — 퓨어웹·토스/카카오 공통, VOCAB에서 확인한 실제 함수명 사용
    #if WEBGL_PUREWEB
    onComplete?.Invoke(true);
    return;
    #else
    // 나중에 platform-porter가 여기(HLSDK 서버 동기화만)를 채운다 — allData를 그대로 재사용, 로컬 저장은 이미 위에서 끝남
    #endif
#else
    // 기존 서버 저장 로직
#endif
}
```

## 8-A. 저장 키 분리

```csharp
#if UNITY_WEBGL && WEBGL_DEV_VER
    private const string SAVE_KEY = "{GameName}_Data_DEV";
#elif UNITY_WEBGL && WEBGL_LIVE_VER
    private const string SAVE_KEY = "{GameName}_Data_LIVE";
#else
    private const string SAVE_KEY = "Data"; // 기존 키 유지
#endif
```

## 8-B. Base64 인코딩 래핑

```csharp
// 저장 (예시 — 실제 구조에 맞게 조정)
public void SaveGameData()
{
    try
    {
        string json = JsonUtility.ToJson(data);
#if UNITY_WEBGL
        string encoded = System.Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes(json));
        PlayerPrefs.SetString(SAVE_KEY, encoded);
#else
        PlayerPrefs.SetString(SAVE_KEY, json);
#endif
        PlayerPrefs.Save();
    }
    catch (System.Exception e)
    {
        Debug.LogError($"[Save] 저장 실패 (JSON 직렬화/Base64 인코딩): {e.Message}");
    }
}

// 불러오기 (예시)
public void LoadGameData()
{
    string stored = PlayerPrefs.GetString(SAVE_KEY, "");
    if (string.IsNullOrEmpty(stored)) return;
    try
    {
#if UNITY_WEBGL
        string json = System.Text.Encoding.UTF8.GetString(System.Convert.FromBase64String(stored));
        data = JsonUtility.FromJson<GameData>(json);
#else
        data = JsonUtility.FromJson<GameData>(stored);
#endif
    }
    catch (System.Exception e)
    {
        Debug.LogError($"[Load] 불러오기 실패 (저장 데이터 손상 가능 — Base64 디코딩/JSON 역직렬화): {e.Message}");
        data = new GameData(); // 기본값 폴백 — 손상된 저장 데이터로 크래시 방지
    }
}
```

## 10. CheatConsole.prefab 씬 추가

```csharp
#if WEBGL_DEBUG_CONSOLE
    RegisterCheats(); // 게임 진입점 내부, 플랫폼 분기 직전에 호출
#endif

// #if UNITY_WEBGL || UNITY_EDITOR — 에디터 비-WebGL 타겟에서도 컴파일되도록
void RegisterCheats()
{
    CheatRegister.ClearAll();
    CheatRegister.Register("Cheat Name", "Description in English", Color.yellow, () => { /* 동작 */ });
    CheatRegister.Build();
}
```
