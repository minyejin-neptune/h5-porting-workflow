using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

public class FontReplaceTool : EditorWindow
{
    // Unity 내장 LegacyRuntime 폰트의 YAML 참조 고정값
    const string LEGACY_RUNTIME_REF = "{fileID: 10102, guid: 0000000000000000e000000000000000, type: 0}";

    bool fromBuiltin = true;
    Font fromFont;
    Font toFont;

    [MenuItem("Tools/H5/Replace Font")]
    static void Open() => GetWindow<FontReplaceTool>("Replace Font").Show();

    void OnGUI()
    {
        EditorGUILayout.Space(8);

        // --- From ---
        EditorGUILayout.LabelField("From", EditorStyles.boldLabel);
        fromBuiltin = EditorGUILayout.ToggleLeft("Unity 내장 LegacyRuntime", fromBuiltin);
        using (new EditorGUI.DisabledScope(fromBuiltin))
            fromFont = (Font)EditorGUILayout.ObjectField("  폰트", fromFont, typeof(Font), false);

        EditorGUILayout.Space(8);

        // --- To ---
        EditorGUILayout.LabelField("To", EditorStyles.boldLabel);
        toFont = (Font)EditorGUILayout.ObjectField("  폰트", toFont, typeof(Font), false);

        EditorGUILayout.Space(12);

        bool canRun = toFont != null && (fromBuiltin || fromFont != null);
        using (new EditorGUI.DisabledScope(!canRun))
        {
            if (GUILayout.Button("Replace 실행", GUILayout.Height(30)))
                Run();
        }

        if (!canRun)
            EditorGUILayout.HelpBox("To 폰트를 선택하세요.", MessageType.Info);
    }

    void Run()
    {
        string fromRef = BuildRef(fromBuiltin, fromFont);
        string toRef   = BuildRef(false, toFont);

        if (fromRef == null || toRef == null)
        {
            EditorUtility.DisplayDialog("오류", "폰트 참조를 생성할 수 없습니다.", "확인");
            return;
        }

        if (fromRef == toRef)
        {
            EditorUtility.DisplayDialog("오류", "From과 To 폰트가 동일합니다.", "확인");
            return;
        }

        // 씬 폴더명은 프로젝트마다 달라(Scene/Scenes 등) 폴더 경로를 추측하지 않는다 —
        // 대신 EditorBuildSettings에 등록된 실제 씬 목록을 그대로 쓴다(project-relative path).
        string[] scenePaths = EditorBuildSettings.scenes.Select(s => s.path).ToArray();

        // 프리팹은 별도 레지스트리가 없어 Assets 전체를 스캔한다 — 회사 SDK(HyperLane)는 수정 금지 대상이라 제외.
        // 사람이 버튼을 눌러 1회 실행하는 Editor 툴이라 텍스트 스캔 비용은 문제 되지 않는다.
        string[] prefabPaths = Directory.GetFiles(Application.dataPath, "*.prefab", SearchOption.AllDirectories)
            .Where(p => !p.Replace('\\', '/').Contains("/HyperLane/"))
            .ToArray();

        int fileCount = 0, replaceCount = 0;
        var log = new StringBuilder();

        foreach (string p in scenePaths)  Process(p, fromRef, toRef, ref fileCount, ref replaceCount, log);
        foreach (string p in prefabPaths) Process(p, fromRef, toRef, ref fileCount, ref replaceCount, log);

        AssetDatabase.Refresh();

        string msg = $"완료: {fileCount}개 파일, 총 {replaceCount}개 교체\n\n{log}";
        Debug.Log("[FontReplaceTool] " + msg);
        EditorUtility.DisplayDialog("Replace Font", msg, "확인");
    }

    static string BuildRef(bool builtin, Font font)
    {
        if (builtin) return LEGACY_RUNTIME_REF;
        if (font == null) return null;

        string path = AssetDatabase.GetAssetPath(font);
        string guid = AssetDatabase.AssetPathToGUID(path);
        AssetDatabase.TryGetGUIDAndLocalFileIdentifier(font, out _, out long fileId);
        return $"{{fileID: {fileId}, guid: {guid}, type: 3}}";
    }

    static void Process(string path, string fromRef, string toRef, ref int fileCount, ref int replaceCount, StringBuilder log)
    {
        string text = File.ReadAllText(path, Encoding.UTF8);
        if (!text.Contains(fromRef)) return;

        int count = 0;
        string result = StringReplace(text, fromRef, toRef, ref count);
        File.WriteAllText(path, result, Encoding.UTF8);

        fileCount++;
        replaceCount += count;
        log.AppendLine($"  {count,3}개  {Path.GetFileName(path)}");
    }

    static string StringReplace(string src, string from, string to, ref int count)
    {
        var sb = new StringBuilder(src.Length);
        int pos = 0;
        while (true)
        {
            int idx = src.IndexOf(from, pos, System.StringComparison.Ordinal);
            if (idx < 0) { sb.Append(src, pos, src.Length - pos); break; }
            sb.Append(src, pos, idx - pos);
            sb.Append(to);
            pos = idx + from.Length;
            count++;
        }
        return sb.ToString();
    }
}
