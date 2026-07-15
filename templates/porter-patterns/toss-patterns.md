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

**다건 임계값 기반 프로모션 패턴 (prefix + Dictionary):**

동일 prefix로 여러 개가 존재하고 트리거가 숫자 임계값인 경우(예: `NORMAL_PLAY_3`, `NORMAL_PLAY_7`, `NORMAL_PLAY_15`) 개별 하드코딩 대신 사용한다. `RefreshManagedPromotions` 결과를 prefix 제거 후 파싱한 임계값 기준 `Dictionary`로 캐싱해두면, 체크 시점마다 목록을 순회(`for`)하지 않고 `TryGetValue`로 O(1) 조회할 수 있다.

```csharp
private const string NormalPlayPromotionPrefix = "NORMAL_PLAY_";
private readonly Dictionary<int, string> normalPlayPromotionIdByThreshold = new Dictionary<int, string>();

public void RefreshNormalPlayPromotions()
{
    (HLSDK.Instance.Provider as TossHandler)?.RefreshManagedPromotions(_ => BuildNormalPlayPromotionLookup());
}

private void BuildNormalPlayPromotionLookup()
{
    normalPlayPromotionIdByThreshold.Clear();
    foreach (PromotionInfoItem promo in TossHandler.ManagedPromotions)
    {
        if (promo.promotionId == null || !promo.promotionId.StartsWith(NormalPlayPromotionPrefix)) continue;
        if (!int.TryParse(promo.promotionId.Substring(NormalPlayPromotionPrefix.Length), out int threshold)) continue;
        normalPlayPromotionIdByThreshold[threshold] = promo.promotionId;
    }
}

// 트리거 시점(예: TotalPlayCount 갱신 직후)에서 호출 — for문 없이 O(1) 조회
public void CheckNormalPlayPromotion(int triggerValue)
{
    var handler = HLSDK.Instance.Provider as TossHandler;
    if (normalPlayPromotionIdByThreshold.TryGetValue(triggerValue, out string promotionId))
    {
        handler.ClaimPromotionRewardForGameForManaged(promotionId);
    }
}
```

**V1 모드 패턴:**

```csharp
#if UNITY_WEBGL && WEBGL_TOSS
HLSDK.Instance.ClaimPromotionRewardForGame("first_play");
#endif
```
