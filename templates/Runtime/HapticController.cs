namespace HLSDK
{
    public enum HapticTier
    {
        Weak,         // 약함
        WeakStrong,   // 약함보다 센 단계
        Medium,       // 중간
        MediumStrong, // 중간보다 센 단계
        Soft,         // softMedium — 플랫폼 무관
        Tap,
        Success,
        Confetti,
    }

    public static class HapticController
    {
        public static void Generate(HapticTier tier)
        {
#if UNITY_WEBGL
            bool isAndroid = HLSDK.Instance.GetDeviceOS() == DeviceOS.ANDROID;
            string type;

            switch (tier)
            {
                case HapticTier.Weak:
                    type = isAndroid ? "basicWeak" : "tickWeak";
                    break;
                case HapticTier.WeakStrong:
                    type = isAndroid ? "tickWeak" : "basicWeak";
                    break;
                case HapticTier.Medium:
                    type = isAndroid ? "basicMedium" : "tickMedium";
                    break;
                case HapticTier.MediumStrong:
                    type = isAndroid ? "tickMedium" : "basicMedium";
                    break;
                case HapticTier.Soft:
                    type = "softMedium";
                    break;
                case HapticTier.Success:
                    type = "success";
                    break;
                case HapticTier.Confetti:
                    type = "confetti";
                    break;
                default:
                    type = "tap";
                    break;
            }

            HLSDK.Instance.GenerateHapticFeedback(type);
#endif
        }
    }
}

