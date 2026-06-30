using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.U2D;

public class TextureFormatSetter : EditorWindow
{
    enum AssetType { Texture, SpriteAtlas }

    AssetType _assetType = AssetType.Texture;
    string _platform = "WebGL";
    TextureImporterFormat _format = TextureImporterFormat.ASTC_12x12;

    List<string> _folderGuids = new List<string>();
    string _resultLog = "";
    Vector2 _scroll;
    Vector2 _folderScroll;

    static string PrefsKey => $"TextureFormatSetter_{Application.productName}_Folders";

    [MenuItem("Tools/Texture Platform Format Setter")]
    static void Open() => GetWindow<TextureFormatSetter>("Texture Format Setter");

    void OnEnable() => LoadFolders();

    void LoadFolders()
    {
        _folderGuids.Clear();
        string saved = EditorPrefs.GetString(PrefsKey, "");
        if (string.IsNullOrEmpty(saved)) return;
        foreach (var guid in saved.Split('|'))
            if (!string.IsNullOrEmpty(guid)) _folderGuids.Add(guid);
    }

    void SaveFolders()
    {
        EditorPrefs.SetString(PrefsKey, string.Join("|", _folderGuids));
    }

    void OnGUI()
    {
        GUILayout.Label("설정", EditorStyles.boldLabel);

        _assetType = (AssetType)EditorGUILayout.EnumPopup("에셋 타입", _assetType);
        _platform = EditorGUILayout.TextField("플랫폼", _platform);
        _format = (TextureImporterFormat)EditorGUILayout.EnumPopup("포맷", _format);

        EditorGUILayout.Space(8);
        GUILayout.Label("대상 폴더", EditorStyles.boldLabel);

        _folderScroll = EditorGUILayout.BeginScrollView(_folderScroll, GUILayout.MaxHeight(120));
        int removeIndex = -1;
        for (int i = 0; i < _folderGuids.Count; i++)
        {
            EditorGUILayout.BeginHorizontal();
            string path = AssetDatabase.GUIDToAssetPath(_folderGuids[i]);
            bool missing = string.IsNullOrEmpty(path);

            var prevColor = GUI.contentColor;
            if (missing) GUI.contentColor = new Color(1f, 0.4f, 0.4f);
            EditorGUILayout.LabelField(missing ? "(missing)" : path, GUILayout.ExpandWidth(true));
            GUI.contentColor = prevColor;

            if (GUILayout.Button("×", GUILayout.Width(24))) removeIndex = i;
            EditorGUILayout.EndHorizontal();
        }
        if (removeIndex >= 0) { _folderGuids.RemoveAt(removeIndex); SaveFolders(); }
        EditorGUILayout.EndScrollView();

        var draggedFolder = EditorGUILayout.ObjectField("폴더 추가", null, typeof(DefaultAsset), false);
        if (draggedFolder != null)
        {
            string folderPath = AssetDatabase.GetAssetPath(draggedFolder);
            if (AssetDatabase.IsValidFolder(folderPath))
            {
                string guid = AssetDatabase.AssetPathToGUID(folderPath);
                if (!_folderGuids.Contains(guid)) { _folderGuids.Add(guid); SaveFolders(); }
            }
        }

        EditorGUILayout.Space(8);
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Set Format")) RunSet();
        if (GUILayout.Button("Verify")) RunVerify();
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.Space(8);
        GUILayout.Label("결과", EditorStyles.boldLabel);
        _scroll = EditorGUILayout.BeginScrollView(_scroll, GUILayout.ExpandHeight(true));
        EditorGUILayout.TextArea(_resultLog, GUILayout.ExpandHeight(true));
        EditorGUILayout.EndScrollView();

        if (GUILayout.Button("로그 지우기")) _resultLog = "";
    }

    IEnumerable<string> ValidFolderPaths()
    {
        foreach (var guid in _folderGuids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (!string.IsNullOrEmpty(path)) yield return path;
        }
    }

    void RunSet()
    {
        string filter = _assetType == AssetType.SpriteAtlas ? "t:SpriteAtlas" : "t:Texture2D";
        var folders = new List<string>(ValidFolderPaths());
        if (folders.Count == 0) { _resultLog = "유효한 폴더 없음"; return; }

        string[] guids = AssetDatabase.FindAssets(filter, folders.ToArray());
        var changed = new List<string>();
        var skipped = new List<string>();
        var noWebGL = new List<string>();

        try
        {
            for (int i = 0; i < guids.Length; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);

                bool cancel = EditorUtility.DisplayCancelableProgressBar(
                    $"포맷 설정 중 ({_platform} / {_format})",
                    path,
                    (float)i / guids.Length);
                if (cancel) break;

                if (_assetType == AssetType.SpriteAtlas)
                {
                    var result = SetAtlasFormat(path);
                    if (result == SetResult.Changed) changed.Add(path);
                    else if (result == SetResult.Skipped) skipped.Add(path);
                    else noWebGL.Add(path);
                }
                else
                {
                    var texImporter = AssetImporter.GetAtPath(path) as TextureImporter;
                    if (texImporter == null) { noWebGL.Add(path); continue; }

                    var settings = texImporter.GetPlatformTextureSettings(_platform);
                    if (settings.overridden && settings.format == _format) { skipped.Add(path); continue; }

                    settings.overridden = true;
                    settings.format = _format;
                    texImporter.SetPlatformTextureSettings(settings);
                    texImporter.SaveAndReimport();
                    changed.Add(path);
                }
            }
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }

        if (changed.Count > 0) AssetDatabase.SaveAssets();

        _resultLog = $"[Set] 변경: {changed.Count}개 / 스킵: {skipped.Count}개 / WebGL 항목 없음: {noWebGL.Count}개\n\n";
        if (changed.Count > 0) _resultLog += "변경된 파일:\n" + string.Join("\n", changed) + "\n\n";
        if (noWebGL.Count > 0) _resultLog += "WebGL 항목 없음:\n" + string.Join("\n", noWebGL);

        Repaint();
    }

    void RunVerify()
    {
        string filter = _assetType == AssetType.SpriteAtlas ? "t:SpriteAtlas" : "t:Texture2D";
        var folders = new List<string>(ValidFolderPaths());
        if (folders.Count == 0) { _resultLog = "유효한 폴더 없음"; return; }

        string[] guids = AssetDatabase.FindAssets(filter, folders.ToArray());
        var fail = new List<string>();

        for (int i = 0; i < guids.Length; i++)
        {
            string path = AssetDatabase.GUIDToAssetPath(guids[i]);

            bool cancel = EditorUtility.DisplayCancelableProgressBar(
                $"검증 중 ({_platform} / {_format})",
                path,
                (float)i / guids.Length);
            if (cancel) break;

            if (_assetType == AssetType.SpriteAtlas)
            {
                if (!GetAtlasFormat(path, out int fmt, out bool overridden))
                    fail.Add($"{path}  (WebGL 항목 없음)");
                else if (!overridden || fmt != (int)_format)
                    fail.Add($"{path}  (현재: {(TextureImporterFormat)fmt}, overridden: {overridden})");
            }
            else
            {
                var texImporter = AssetImporter.GetAtPath(path) as TextureImporter;
                if (texImporter == null) { fail.Add($"{path}  (importer null)"); continue; }

                var settings = texImporter.GetPlatformTextureSettings(_platform);
                if (!settings.overridden || settings.format != _format)
                    fail.Add($"{path}  (현재: {settings.format}, overridden: {settings.overridden})");
            }
        }

        EditorUtility.ClearProgressBar();

        if (fail.Count == 0)
            _resultLog = $"[Verify] 통과 — {guids.Length}개 모두 {_format}";
        else
            _resultLog = $"[Verify] 실패 {fail.Count}개 / 전체 {guids.Length}개\n\n" + string.Join("\n", fail);

        Repaint();
    }

    enum SetResult { Changed, Skipped, NoWebGL }

    SetResult SetAtlasFormat(string path)
    {
        var atlas = AssetDatabase.LoadAssetAtPath<SpriteAtlas>(path);
        if (atlas == null) return SetResult.NoWebGL;

        var so = new SerializedObject(atlas);
        var platformSettings = so.FindProperty("m_EditorData.platformSettings");
        if (platformSettings == null) return SetResult.NoWebGL;

        for (int j = 0; j < platformSettings.arraySize; j++)
        {
            var entry = platformSettings.GetArrayElementAtIndex(j);
            if (entry.FindPropertyRelative("m_BuildTarget").stringValue != _platform) continue;

            var formatProp = entry.FindPropertyRelative("m_TextureFormat");
            var overriddenProp = entry.FindPropertyRelative("m_Overridden");

            if (overriddenProp.boolValue && formatProp.intValue == (int)_format)
                return SetResult.Skipped;

            formatProp.intValue = (int)_format;
            overriddenProp.boolValue = true;
            so.ApplyModifiedProperties();
            EditorUtility.SetDirty(atlas);
            return SetResult.Changed;
        }

        return SetResult.NoWebGL;
    }

    bool GetAtlasFormat(string path, out int format, out bool overridden)
    {
        format = -1;
        overridden = false;

        var atlas = AssetDatabase.LoadAssetAtPath<SpriteAtlas>(path);
        if (atlas == null) return false;

        var so = new SerializedObject(atlas);
        var platformSettings = so.FindProperty("m_EditorData.platformSettings");
        if (platformSettings == null) return false;

        for (int j = 0; j < platformSettings.arraySize; j++)
        {
            var entry = platformSettings.GetArrayElementAtIndex(j);
            if (entry.FindPropertyRelative("m_BuildTarget").stringValue != _platform) continue;

            format = entry.FindPropertyRelative("m_TextureFormat").intValue;
            overridden = entry.FindPropertyRelative("m_Overridden").boolValue;
            return true;
        }

        return false;
    }
}
