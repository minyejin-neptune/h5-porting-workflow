# toss-porter 코드 패턴 참고 문서

> toss-porter.md의 각 스텝에서 참조한다. 이 파일 단독으로는 읽지 않는다.

## 5-1. 배너 광고

```csharp
// 기존 배너 Init 함수 안에
#if UNITY_WEBGL && WEBGL_TOSS
var toss = HLSDK.Instance.Provider as TossHandler;
if (!_isBannerInitialized)
{
    _isBannerInitialized = true;
    toss.InitializeAppsInTossBannerAd(result => { });
}
#endif

// 기존 배너 Attach 함수 안에 (씬 진입마다 호출되는 곳)
#if UNITY_WEBGL && WEBGL_TOSS
toss.AttachAppsInTossBannerAd(result => { });
#endif

// 기존 배너 Detach 함수 안에 (씬 이탈 시 호출되는 곳)
#if UNITY_WEBGL && WEBGL_TOSS
toss.DetachAppsInTossBannerAd();
#endif
```

## 12. 프로모션

**Managed 모드 패턴:**

```csharp
var toss = HLSDK.Instance.Provider as TossHandler;

// QuickLogin 환경 — 클라이언트 직접 지급
toss.ClaimPromotionRewardForGameForManaged("first_play_reward");

// Login 환경 — 서버 경유 지급
toss.ClaimPromotionRewardByServerForManaged("first_play_reward");

// UI 메뉴 열기 직전 최신 목록 갱신 (필요 시만)
toss.RefreshManagedPromotions(result => { if (result.success) /* UI 갱신 */; });
```

**V1 모드 패턴:**

```csharp
#if UNITY_WEBGL && WEBGL_TOSS
HLSDK.Instance.ClaimPromotionRewardForGame("first_play");
#endif
```
