using UnityEngine;

/// <summary>
/// Toss WebGL SafeArea 적용 컴포넌트.
/// - RectTransform(UI): 세로 스트레치는 offset, 점앵커는 위치로 상/하 inset을 적용한다.
/// - 일반 Transform(SpriteRenderer 등 월드 오브젝트): orthographic 카메라로 px→월드 유닛 변환 후
///   지정한 가장자리(_worldAnchor) 방향으로 localPosition을 이동한다.
/// </summary>
public class SafeAreaAdjuster : MonoBehaviour
{
#if UNITY_WEBGL
    #if WEBGL_TOSS
    [SerializeField] private float OffsetPaddingTop = 50f;
    [SerializeField] private float OffsetPaddingBottom = 0f;
    #else
    [SerializeField] private float OffsetPaddingTop = 0f;
    [SerializeField] private float OffsetPaddingBottom = 0f;
    #endif
#else
    [SerializeField] private float OffsetPaddingTop = 0f;
    [SerializeField] private float OffsetPaddingBottom = 0f;
#endif

    // 월드 오브젝트(RectTransform 없음)가 화면 어느 가장자리에 붙는지 — 그쪽 inset만 적용한다.
    private enum WorldAnchor { Top, Bottom }

    [SerializeField] private WorldAnchor _worldAnchor = WorldAnchor.Top;
    // 비어 있으면 Camera.main 사용.
    [SerializeField] private Camera _worldCamera;

    // 월드 오브젝트가 실제 적용한 월드 Y 이동량을 알린다(음수=아래로). 값이 바뀔 때만 발생.
    public event System.Action<float> OnWorldOffsetApplied;

    [SerializeField] private RectTransform _panel;  // 비우면 Awake에서 GetComponent 폴백
    private Vector3 _worldBaseLocalPos;
    private bool _worldBaseCaptured;
    private float _lastWorldOffsetY = float.NaN;

    private void Awake()
    {
        // 인스펙터 지정이 없으면 GetComponent 폴백. 월드 오브젝트면 둘 다 null → World 경로.
        if (_panel == null)
            _panel = GetComponent<RectTransform>();
    }

    private void Start()
    {
        ApplyOffset();
    }

    private void ApplyOffset()
    {
        float insetTop = 0f;
        float insetBottom = 0f;
#if UNITY_WEBGL
        insetTop = HLSDK.Instance.GetSafeAreaTop();
        insetBottom = HLSDK.Instance.GetSafeAreaBottom();
#endif

        float totalTop = OffsetPaddingTop + insetTop;
        float totalBottom = OffsetPaddingBottom + insetBottom;

        if (_panel != null)
        {
            ApplyRectOffset(totalTop, totalBottom);
        }
        else
        {
            ApplyWorldOffset(totalTop, totalBottom);
        }
    }

    // RectTransform(UI)용: 세로 스트레치면 offset, 점앵커면 위치로 상/하 inset을 기존 값에 더해 적용.
    private void ApplyRectOffset(float totalTop, float totalBottom)
    {
        if (!Mathf.Approximately(_panel.anchorMin.y, _panel.anchorMax.y))
        {
            Vector2 offsetMin = _panel.offsetMin;
            Vector2 offsetMax = _panel.offsetMax;
            offsetMin.y += totalBottom;
            offsetMax.y -= totalTop;
            _panel.offsetMin = offsetMin;
            _panel.offsetMax = offsetMax;
        }
        else
        {
            Vector2 anchoredPosition = _panel.anchoredPosition;
            if (_panel.anchorMax.y > 0.5f)
            {
                anchoredPosition.y -= totalTop;
            }
            else
            {
                anchoredPosition.y += totalBottom;
            }
            _panel.anchoredPosition = anchoredPosition;
        }
    }

    // SpriteRenderer 등 월드 오브젝트용: 최종 여백(px)을 월드 유닛으로 변환해 localPosition 이동.
    private void ApplyWorldOffset(float totalTop, float totalBottom)
    {
        Camera cam = _worldCamera != null ? _worldCamera : Camera.main;
        // orthographic이 아니면 거리 의존이라 단일 계수로 변환할 수 없어 건너뛴다.
        if (cam == null || !cam.orthographic)
        {
            return;
        }

        // 최초 1회 기준 위치 캡처(다른 컴포넌트의 Awake 위치 설정 이후인 Start 시점).
        if (!_worldBaseCaptured)
        {
            _worldBaseLocalPos = transform.localPosition;
            _worldBaseCaptured = true;
        }

        float worldPerPixel = (cam.orthographicSize * 2f) / Screen.height;
        float deltaY = (_worldAnchor == WorldAnchor.Top)
            ? -(totalTop * worldPerPixel)
            : (totalBottom * worldPerPixel);

        Vector3 pos = _worldBaseLocalPos;
        pos.y = _worldBaseLocalPos.y + deltaY;
        transform.localPosition = pos;

        // 이동량이 바뀔 때만 통지(예: 세이프에어리어 변경).
        if (deltaY != _lastWorldOffsetY)
        {
            _lastWorldOffsetY = deltaY;
            OnWorldOffsetApplied?.Invoke(deltaY);
        }
    }
}
