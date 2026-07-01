using UnityEngine;

/// <summary>
/// Toss WebGL SafeArea 적용 컴포넌트.
/// - RectTransform(UI): 루트에 붙여 상단/하단 inset을 offset으로 적용한다.
/// - 일반 Transform(SpriteRenderer 등 월드 오브젝트): orthographic 카메라로 px→월드 유닛 변환 후
///   지정한 가장자리(_worldAnchor) 방향으로 localPosition을 이동한다.
/// 심볼릭 링크로 연결되므로, 프로젝트 내에서는 직접 수정하지 말 것
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

    private RectTransform _panel;
    private Vector3 _worldBaseLocalPos;
    private bool _worldBaseCaptured;
    private float _lastWorldOffsetY = float.NaN;

    private void Awake()
    {
        // 월드 오브젝트면 RectTransform이 없어 null이 된다.
        _panel = GetComponent<RectTransform>();
    }

    private void Start()
    {
        ApplyOffset();
    }

    private void ApplyOffset()
    {
#if UNITY_WEBGL
        float insetTop = HLSDK.Instance.GetSafeAreaTop();
        float insetBottom = HLSDK.Instance.GetSafeAreaBottom();
#else
        float insetTop = 0f;
        float insetBottom = 0f;
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

    // RectTransform(UI)용: 최종 여백(px)을 offsetMin/offsetMax에 적용.
    private void ApplyRectOffset(float totalTop, float totalBottom)
    {
        _panel.offsetMin = new Vector2(0f, totalBottom);
        _panel.offsetMax = new Vector2(0f, -totalTop);
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
        // Update에서 매 프레임 호출돼도 base+offset로 절대 적용해 누적(드리프트)되지 않게 한다.
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

        // 이동량이 바뀔 때만 통지(예: 세이프에어리어 변경). 매 프레임 스팸 방지.
        if (deltaY != _lastWorldOffsetY)
        {
            _lastWorldOffsetY = deltaY;
            OnWorldOffsetApplied?.Invoke(deltaY);
        }
    }
}
