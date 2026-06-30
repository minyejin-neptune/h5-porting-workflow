#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class CompileChecker
{
    private static readonly Dictionary<string, string> PlatformDefines = new Dictionary<string, string>
    {
        { "PUREWEB", "UNITY_WEBGL;WEBGL_PUREWEB;WEBGL_DEV_VER;WEBGL_DEBUG_CONSOLE" },
        { "PUREWEB_LIVE", "UNITY_WEBGL;WEBGL_PUREWEB;WEBGL_LIVE_VER" },
        { "TOSS", "UNITY_WEBGL;WEBGL_TOSS;WEBGL_DEV_VER;WEBGL_DEBUG_CONSOLE" },
        { "TOSS_LIVE", "UNITY_WEBGL;WEBGL_TOSS;WEBGL_LIVE_VER" },
        { "ANDROID", "" },
    };

    private static readonly Dictionary<string, (BuildTargetGroup group, BuildTarget target)> PlatformTargets =
        new Dictionary<string, (BuildTargetGroup, BuildTarget)>
    {
        { "PUREWEB", (BuildTargetGroup.WebGL, BuildTarget.WebGL) },
        { "PUREWEB_LIVE", (BuildTargetGroup.WebGL, BuildTarget.WebGL) },
        { "TOSS", (BuildTargetGroup.WebGL, BuildTarget.WebGL) },
        { "TOSS_LIVE", (BuildTargetGroup.WebGL, BuildTarget.WebGL) },
        { "ANDROID", (BuildTargetGroup.Android, BuildTarget.Android) },
    };

    private const string ResultLogPath = "Docs/porting/compile_result.log";
    private const string PlatformFilePath = "Docs/porting/.compile_platform";

    // 배치모드 진입점: Unity -batchmode -executeMethod CompileChecker.Run -customArgs PUREWEB
    public static void Run()
    {
        string platform = GetArgValue("-customArgs");
        if (string.IsNullOrEmpty(platform))
        {
            WriteErrorLog("플랫폼 인자 없음. -customArgs PUREWEB 또는 TOSS 를 지정하세요.");
            EditorApplication.Exit(1);
            return;
        }

        platform = platform.ToUpper();
        if (!PlatformDefines.ContainsKey(platform))
        {
            WriteErrorLog($"알 수 없는 플랫폼: {platform}. 지원 플랫폼: {string.Join(", ", PlatformDefines.Keys)}");
            EditorApplication.Exit(1);
            return;
        }

        RunCheck(platform);
    }

    [MenuItem("Tools/H5/Compile Check/PureWeb DEV")]
    public static void RunPureWebDev() => RunCheck("PUREWEB");

    [MenuItem("Tools/H5/Compile Check/PureWeb LIVE")]
    public static void RunPureWebLive() => RunCheck("PUREWEB_LIVE");

    [MenuItem("Tools/H5/Compile Check/Toss DEV")]
    public static void RunTossDev() => RunCheck("TOSS");

    [MenuItem("Tools/H5/Compile Check/Toss LIVE")]
    public static void RunTossLive() => RunCheck("TOSS_LIVE");

    [MenuItem("Tools/H5/Compile Check/Android")]
    public static void RunAndroidFromMenu() => RunCheck("ANDROID");

    // Claude Code 배치모드·파일 트리거용 — 다이얼로그 없이 바로 실행
    [MenuItem("Tools/H5/Compile Check")]
    public static void RunFromMenu()
    {
        if (File.Exists(PlatformFilePath))
        {
            string platform = File.ReadAllText(PlatformFilePath).Trim().ToUpper();
            File.Delete(PlatformFilePath);

            if (PlatformDefines.ContainsKey(platform))
            {
                RunCheck(platform);
                return;
            }
        }

        // 파일 없을 때 fallback: 다이얼로그 (DEV 기준)
        int choice = EditorUtility.DisplayDialogComplex(
            "H5 컴파일 체크",
            "검증할 플랫폼을 선택하세요. (DEV 심볼 기준)",
            "PureWeb DEV",
            "Toss DEV",
            "취소"
        );

        switch (choice)
        {
            case 0: RunCheck("PUREWEB"); break;
            case 1: RunCheck("TOSS"); break;
        }
    }

    public static void RunCheck(string platform)
    {
        string platformDefines = PlatformDefines[platform];
        var (targetGroup, buildTarget) = PlatformTargets[platform];

        // 1. 원래 빌드 타겟 저장 (복원용)
        BuildTarget originalTarget = EditorUserBuildSettings.activeBuildTarget;
        BuildTargetGroup originalGroup = BuildPipeline.GetBuildTargetGroup(originalTarget);
        bool targetSwitched = false;

        // 2. 플랫폼 전환
        if (originalTarget != buildTarget)
        {
            Debug.Log($"[CompileChecker] {buildTarget} 플랫폼으로 전환 중...");
            bool switched = EditorUserBuildSettings.SwitchActiveBuildTarget(targetGroup, buildTarget);
            if (!switched)
            {
                WriteErrorLog($"{buildTarget} 플랫폼 전환 실패. 해당 플랫폼 Build Support 설치 여부를 확인하세요.");
                if (Application.isBatchMode) EditorApplication.Exit(1);
                return;
            }
            targetSwitched = true;
        }

        // 2. Android: 배치모드에서 서명 비활성화 (스크립트 컴파일만 체크)
        bool prevUseCustomKeystore = false;
        if (targetGroup == BuildTargetGroup.Android)
        {
            prevUseCustomKeystore = PlayerSettings.Android.useCustomKeystore;
            PlayerSettings.Android.useCustomKeystore = false;
        }

        // 3. 기존 프로젝트 Define Symbols 읽기 + 플랫폼 심볼 병합
        // 플랫폼 전용 심볼은 제거 후 병합 (WEBGL_TOSS ↔ WEBGL_PUREWEB 충돌 방지)
        string existingDefines = PlayerSettings.GetScriptingDefineSymbolsForGroup(targetGroup);
        var platformExclusive = new HashSet<string> {
            "WEBGL_TOSS", "WEBGL_PUREWEB", "WEBGL_DEV_VER", "WEBGL_LIVE_VER",
            "WEBGL_DEBUG_CONSOLE", "ENABLE_LOG"
        };
        var symbolSet = new HashSet<string>();
        foreach (var s in existingDefines.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            if (!platformExclusive.Contains(s))
                symbolSet.Add(s);
        foreach (var sym in platformDefines.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            symbolSet.Add(sym);
        string defines = string.Join(";", symbolSet);

        Debug.Log($"[CompileChecker] 플랫폼: {platform} | Target: {buildTarget}");
        Debug.Log($"[CompileChecker] 기존 심볼: {existingDefines}");
        Debug.Log($"[CompileChecker] 병합 심볼: {defines}");

        PlayerSettings.SetScriptingDefineSymbolsForGroup(targetGroup, defines);

        // 3. 씬 목록 수집
        var scenes = new List<string>();
        foreach (var scene in EditorBuildSettings.scenes)
        {
            if (scene.enabled) scenes.Add(scene.path);
        }
        if (scenes.Count == 0)
        {
            string[] guids = AssetDatabase.FindAssets("t:Scene", new[] { "Assets/Scenes" });
            if (guids.Length > 0)
                scenes.Add(AssetDatabase.GUIDToAssetPath(guids[0]));
        }

        // 4. 스크립트 전용 컴파일
        string tempPath = Path.Combine(Path.GetTempPath(), $"porting_compile_{platform.ToLower()}");
        var buildOptions = new BuildPlayerOptions
        {
            scenes = scenes.ToArray(),
            locationPathName = tempPath,
            target = buildTarget,
            targetGroup = targetGroup,
            options = BuildOptions.BuildScriptsOnly,
        };

        Debug.Log("[CompileChecker] 컴파일 체크 시작...");
        BuildReport report = BuildPipeline.BuildPlayer(buildOptions);

        // 5. Android 서명 설정 복원
        if (targetGroup == BuildTargetGroup.Android)
            PlayerSettings.Android.useCustomKeystore = prevUseCustomKeystore;

        // 6. Define Symbols 복원
        PlayerSettings.SetScriptingDefineSymbolsForGroup(targetGroup, existingDefines);

        // 7. 빌드 타겟 복원 (ProjectSettings.asset 보호)
        if (targetSwitched)
        {
            Debug.Log($"[CompileChecker] 빌드 타겟 복원: {buildTarget} → {originalTarget}");
            EditorUserBuildSettings.SwitchActiveBuildTarget(originalGroup, originalTarget);
        }

        // 8. 결과 저장
        WriteResult(platform, platformDefines, defines, report);

        // 9. 종료 (배치모드만)
        if (Application.isBatchMode)
            EditorApplication.Exit(report.summary.result == BuildResult.Failed ? 1 : 0);
    }

    private static void WriteResult(string platform, string platformDefines, string mergedDefines, BuildReport report)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"[{platform}] 컴파일 체크 결과");
        sb.AppendLine($"생성일: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
        sb.AppendLine($"플랫폼 심볼: {platformDefines}");
        sb.AppendLine($"병합 심볼: {mergedDefines}");
        sb.AppendLine();

        var errors = new List<string>();
        foreach (var step in report.steps)
        {
            foreach (var msg in step.messages)
            {
                if (msg.type != LogType.Error && msg.type != LogType.Exception) continue;
                // C# 컴파일 에러가 아닌 패키징/링킹 단계 에러는 제외
                if (msg.content.Contains("Can't verify script data layout")) continue;
                if (msg.content.Contains("Force skip data build")) continue;
                errors.Add(msg.content);
            }
        }

        if (errors.Count == 0)
        {
            sb.AppendLine("✅ 컴파일 에러 없음");
        }
        else
        {
            sb.AppendLine($"❌ 컴파일 에러 {errors.Count}건");
            sb.AppendLine();
            foreach (var err in errors)
                sb.AppendLine(err);
        }

        string dir = Path.GetDirectoryName(ResultLogPath);
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        File.WriteAllText(ResultLogPath, sb.ToString(), Encoding.UTF8);
        Debug.Log($"[CompileChecker] 결과 저장: {ResultLogPath}");
    }

    private static string GetArgValue(string argName)
    {
        string[] args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (string.Equals(args[i], argName, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        }
        return null;
    }

    private static void WriteErrorLog(string message)
    {
        string dir = Path.GetDirectoryName(ResultLogPath);
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        File.WriteAllText(ResultLogPath, $"[ERROR] {message}\n", Encoding.UTF8);
        Debug.LogError($"[CompileChecker] {message}");
    }
}
#endif
