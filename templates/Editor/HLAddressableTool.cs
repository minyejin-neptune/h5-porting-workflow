using System.Collections.Generic;
using UnityEditor;
using UnityEditor.AddressableAssets;
using UnityEditor.AddressableAssets.Settings;
using UnityEditor.AddressableAssets.Settings.GroupSchemas;
using UnityEngine;

// H5Builder 호환 변수명(RemoteBuildPath / RemoteLoadPath)을 기준으로
// Addressable 그룹 경로 및 프로파일 변수를 관리하는 HyperLane 전용 에디터 툴.
public class HLAddressableTool : EditorWindow
{
    const string kRemoteBuildPath = "RemoteBuildPath";
    const string kRemoteLoadPath = "RemoteLoadPath";

    enum PathType { Local, Remote, Mixed, NA }

    class GroupEntry
    {
        public AddressableAssetGroup group;
        public bool selected;
        public PathType pathType;
    }

    List<GroupEntry> _entries = new List<GroupEntry>();
    Vector2 _scroll;
    bool _variablesOk;

    static readonly GUIStyle _badgeStyle = new GUIStyle(EditorStyles.miniLabel) { alignment = TextAnchor.MiddleCenter };

    // -----------------------------------------------------------------------
    // 초기화
    // -----------------------------------------------------------------------

    [MenuItem("Tools/Addressables/HL Addressable Tool")]
    static void Open()
    {
        var wnd = GetWindow<HLAddressableTool>("HL Addressable Tool");
        wnd.minSize = new Vector2(480, 440);
        wnd.Refresh();
    }

    void OnEnable() => Refresh();

    void Refresh()
    {
        _entries.Clear();
        var settings = AddressableAssetSettingsDefaultObject.Settings;
        if (settings == null) return;

        _variablesOk = GetVariableId(settings, kRemoteBuildPath) != null
                    && GetVariableId(settings, kRemoteLoadPath) != null;

        string remoteBuildId = GetVariableId(settings, kRemoteBuildPath);

        foreach (var group in settings.groups)
        {
            var schema = group.GetSchema<BundledAssetGroupSchema>();
            PathType pathType;

            if (schema == null)
            {
                pathType = PathType.NA;
            }
            else
            {
                string remoteLoadId = GetVariableId(settings, kRemoteLoadPath);
                bool buildIsRemote = schema.BuildPath.Id == remoteBuildId;
                bool loadIsRemote = schema.LoadPath.Id == remoteLoadId;

                if (buildIsRemote && loadIsRemote) pathType = PathType.Remote;
                else if (!buildIsRemote && !loadIsRemote) pathType = PathType.Local;
                else pathType = PathType.Mixed;
            }

            _entries.Add(new GroupEntry
            {
                group = group,
                selected = schema != null,
                pathType = pathType
            });
        }
    }

    static string GetVariableId(AddressableAssetSettings settings, string variableName)
    {
        return settings.profileSettings.GetProfileDataByName(variableName)?.Id;
    }

    // -----------------------------------------------------------------------
    // GUI
    // -----------------------------------------------------------------------

    void OnGUI()
    {
        // 툴바
        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);
        if (GUILayout.Button("Refresh", EditorStyles.toolbarButton, GUILayout.Width(60)))
            Refresh();
        GUILayout.FlexibleSpace();
        EditorGUILayout.EndHorizontal();

        // 변수 상태 패널
        EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
        var prevColor = GUI.contentColor;
        GUI.contentColor = _variablesOk ? new Color(0.5f, 1f, 0.5f) : new Color(1f, 0.6f, 0.4f);
        EditorGUILayout.LabelField(
            _variablesOk
                ? "✓  RemoteLoadPath / RemoteBuildPath 정상"
                : "✗  RemoteLoadPath / RemoteBuildPath 없음 — 변수명 정규화 필요",
            GUILayout.ExpandWidth(true));
        GUI.contentColor = prevColor;
        using (new EditorGUI.DisabledScope(_variablesOk))
        {
            if (GUILayout.Button("변수명 정규화", GUILayout.Width(100)))
                NormalizeProfileVariables();
        }
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.Space(4);

        // 액션 버튼 영역
        EditorGUILayout.BeginHorizontal();
        if (GUILayout.Button("Select All", GUILayout.Width(90))) SelectAll(true);
        if (GUILayout.Button("Deselect All", GUILayout.Width(90))) SelectAll(false);
        GUILayout.FlexibleSpace();
        using (new EditorGUI.DisabledScope(!HasSelected()))
        {
            if (GUILayout.Button("Set to Remote", GUILayout.Width(110))) ApplyPath(remote: true);
            if (GUILayout.Button("Set to Local", GUILayout.Width(110))) ApplyPath(remote: false);
        }
        EditorGUILayout.EndHorizontal();

        EditorGUILayout.Space(4);

        // 헤더
        EditorGUILayout.BeginHorizontal(EditorStyles.helpBox);
        GUILayout.Space(24);
        EditorGUILayout.LabelField("Group Name", EditorStyles.boldLabel, GUILayout.ExpandWidth(true));
        EditorGUILayout.LabelField("Status", EditorStyles.boldLabel, GUILayout.Width(60));
        EditorGUILayout.EndHorizontal();

        // 그룹 목록
        _scroll = EditorGUILayout.BeginScrollView(_scroll);
        foreach (var entry in _entries)
        {
            EditorGUILayout.BeginHorizontal();

            bool canSelect = entry.pathType != PathType.NA;
            EditorGUI.BeginDisabledGroup(!canSelect);
            entry.selected = EditorGUILayout.Toggle(entry.selected, GUILayout.Width(20));
            EditorGUI.EndDisabledGroup();

            EditorGUILayout.LabelField(entry.group.name, GUILayout.ExpandWidth(true));

            Color prev = GUI.contentColor;
            GUI.contentColor = entry.pathType switch
            {
                PathType.Remote => new Color(0.4f, 0.8f, 1f),
                PathType.Local => new Color(0.5f, 1f, 0.5f),
                PathType.Mixed => new Color(1f, 0.9f, 0.3f),
                _ => new Color(0.6f, 0.6f, 0.6f)
            };
            GUILayout.Label(entry.pathType.ToString(), _badgeStyle, GUILayout.Width(60));
            GUI.contentColor = prev;

            EditorGUILayout.EndHorizontal();
        }
        EditorGUILayout.EndScrollView();

        EditorGUILayout.Space(2);

        int selectedCount = _entries.FindAll(e => e.selected).Count;
        EditorGUILayout.LabelField($"선택: {selectedCount} / 전체: {_entries.Count}", EditorStyles.miniLabel);
    }

    // -----------------------------------------------------------------------
    // 제어
    // -----------------------------------------------------------------------

    void SelectAll(bool value)
    {
        foreach (var e in _entries)
            if (e.pathType != PathType.NA) e.selected = value;
    }

    bool HasSelected() => _entries.Exists(e => e.selected);

    // Remote.BuildPath / Remote.LoadPath → RemoteBuildPath / RemoteLoadPath
    // H5Builder가 기대하는 변수명이 없을 때 기존 값을 복사해 생성.
    void NormalizeProfileVariables()
    {
        var settings = AddressableAssetSettingsDefaultObject.Settings;
        if (settings == null) return;

        var profileSettings = settings.profileSettings;
        bool changed = false;

        changed |= EnsureVariable(settings, profileSettings,
            AddressableAssetSettings.kRemoteBuildPath, kRemoteBuildPath);
        changed |= EnsureVariable(settings, profileSettings,
            AddressableAssetSettings.kRemoteLoadPath, kRemoteLoadPath);

        if (changed)
        {
            EditorUtility.SetDirty(settings);
            AssetDatabase.SaveAssets();
            Refresh();
            Repaint();
            Debug.Log("[HLAddressableTool] 변수명 정규화 완료 — RemoteBuildPath / RemoteLoadPath 추가됨");
        }
    }

    // newName이 없으면 oldName 값을 복사해 생성. 반환값: 실제로 생성했는지 여부.
    static bool EnsureVariable(AddressableAssetSettings settings,
        AddressableAssetProfileSettings profileSettings,
        string oldName, string newName)
    {
        if (GetVariableId(settings, newName) != null) return false;

        var oldData = profileSettings.GetProfileDataByName(oldName);
        string defaultValue = oldData != null
            ? profileSettings.GetValueById(settings.activeProfileId, oldData.Id) ?? ""
            : "";

        profileSettings.CreateValue(newName, defaultValue);

        // 기존 변수가 있으면 모든 프로파일에 같은 값 복사
        if (oldData != null)
        {
            foreach (string profileName in profileSettings.GetAllProfileNames())
            {
                string profileId = profileSettings.GetProfileId(profileName);
                string value = profileSettings.GetValueById(profileId, oldData.Id);
                if (value != null)
                    profileSettings.SetValue(profileId, newName, value);
            }
        }

        return true;
    }

    void ApplyPath(bool remote)
    {
        var settings = AddressableAssetSettingsDefaultObject.Settings;
        if (settings == null) return;

        var selected = _entries.FindAll(e => e.selected);
        var changed = new List<string>();
        var skipped = new List<string>();

        try
        {
            for (int i = 0; i < selected.Count; i++)
            {
                var entry = selected[i];

                bool cancel = EditorUtility.DisplayCancelableProgressBar(
                    remote ? "Remote 경로 설정 중" : "Local 경로 설정 중",
                    entry.group.name,
                    (float)i / selected.Count);
                if (cancel) break;

                var schema = entry.group.GetSchema<BundledAssetGroupSchema>();
                if (schema == null)
                {
                    skipped.Add(entry.group.name);
                    continue;
                }

                if (remote)
                {
                    schema.BuildPath.SetVariableByName(settings, kRemoteBuildPath);
                    schema.LoadPath.SetVariableByName(settings, kRemoteLoadPath);
                }
                else
                {
                    schema.BuildPath.SetVariableByName(settings, AddressableAssetSettings.kLocalBuildPath);
                    schema.LoadPath.SetVariableByName(settings, AddressableAssetSettings.kLocalLoadPath);
                }

                EditorUtility.SetDirty(schema);
                changed.Add(entry.group.name);
            }
        }
        finally
        {
            EditorUtility.ClearProgressBar();
        }

        AssetDatabase.SaveAssets();
        Refresh();
        Repaint();

        string label = remote ? "Remote" : "Local";
        Debug.Log($"[HLAddressableTool] {label} 설정 완료 — 변경: {changed.Count}개 / 스킵: {skipped.Count}개");
        if (changed.Count > 0)
            Debug.Log("[HLAddressableTool] 변경된 그룹:\n" + string.Join("\n", changed));
        if (skipped.Count > 0)
            Debug.LogWarning("[HLAddressableTool] 스킵된 그룹:\n" + string.Join("\n", skipped));
    }
}
