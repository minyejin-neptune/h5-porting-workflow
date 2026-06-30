#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;
using UnityEditor;
using UnityEngine;

public class CompileResultWindow : EditorWindow
{
    private struct Entry
    {
        public string path;
        public int line;
        public bool isError;
        public string text;
    }

    private const string LogPath = "Docs/porting/compile_result.log";

    private static readonly Regex LineRegex = new Regex(
        @"^(Assets[/\\][^\(]+)\((\d+),\d+\):\s*(error|warning)\s+", RegexOptions.Compiled);

    private string _headerText;
    private bool _hasResult;
    private bool _success;
    private readonly List<Entry> _entries = new List<Entry>();
    private Vector2 _scroll;
    private bool _running;
    private GUIStyle _rowStyle;

    [MenuItem("Tools/H5/Compile Result Window")]
    public static void Open()
    {
        var win = GetWindow<CompileResultWindow>("Compile Results");
        win.minSize = new Vector2(500, 300);
        win.LoadLog();
    }

    private void OnEnable() => LoadLog();

    private void OnGUI()
    {
        if (_rowStyle == null)
            _rowStyle = new GUIStyle(EditorStyles.helpBox) { wordWrap = true, richText = false };

        DrawToolbar();

        if (!string.IsNullOrEmpty(_headerText))
            EditorGUILayout.LabelField(_headerText, EditorStyles.centeredGreyMiniLabel);

        EditorGUILayout.Space(2);

        if (_running)
        {
            EditorGUILayout.HelpBox("컴파일 중...", MessageType.Info);
            return;
        }

        if (!_hasResult)
        {
            EditorGUILayout.HelpBox("로그 없음. 위 버튼으로 컴파일 체크를 실행하세요.", MessageType.None);
            return;
        }

        if (_success)
        {
            EditorGUILayout.HelpBox("✅ 컴파일 에러 없음", MessageType.Info);
            return;
        }

        int errCnt = 0, warnCnt = 0;
        foreach (var e in _entries) { if (e.isError) errCnt++; else warnCnt++; }

        string summary = errCnt > 0
            ? $"에러 {errCnt}건" + (warnCnt > 0 ? $"  /  경고 {warnCnt}건" : "")
            : $"경고 {warnCnt}건";
        EditorGUILayout.HelpBox(summary, errCnt > 0 ? MessageType.Error : MessageType.Warning);

        _scroll = EditorGUILayout.BeginScrollView(_scroll);
        foreach (var e in _entries)
        {
            GUI.color = e.isError ? new Color(1f, 0.7f, 0.7f) : new Color(1f, 0.95f, 0.6f);
            if (GUILayout.Button(e.text, _rowStyle))
                Jump(e);
            GUI.color = Color.white;
        }
        EditorGUILayout.EndScrollView();
    }

    private void DrawToolbar()
    {
        EditorGUILayout.BeginHorizontal(EditorStyles.toolbar);
        GUI.enabled = !_running;
        if (GUILayout.Button("PureWeb", EditorStyles.toolbarButton, GUILayout.Width(68)))
            TriggerCheck("PUREWEB");
        if (GUILayout.Button("Toss", EditorStyles.toolbarButton, GUILayout.Width(48)))
            TriggerCheck("TOSS");
        if (GUILayout.Button("Android", EditorStyles.toolbarButton, GUILayout.Width(58)))
            TriggerCheck("ANDROID");
        GUI.enabled = true;
        GUILayout.FlexibleSpace();
        if (GUILayout.Button("↺  새로고침", EditorStyles.toolbarButton, GUILayout.Width(76)))
            LoadLog();
        EditorGUILayout.EndHorizontal();
    }

    private void TriggerCheck(string platform)
    {
        if (_running) return;
        _running = true;
        Repaint();
        EditorApplication.delayCall += () =>
        {
            CompileChecker.RunCheck(platform);
            _running = false;
            LoadLog();
        };
    }

    private void LoadLog()
    {
        _entries.Clear();
        _hasResult = false;
        _success = false;
        _headerText = "";

        if (!File.Exists(LogPath)) { Repaint(); return; }

        foreach (string raw in File.ReadAllLines(LogPath))
        {
            if (raw.StartsWith("[") && raw.Contains("컴파일 체크 결과"))
            {
                _headerText = raw;
                continue;
            }
            if (raw.StartsWith("생성일:"))
            {
                _headerText += "   " + raw.Replace("생성일: ", "");
                continue;
            }
            if (raw.StartsWith("✅")) { _hasResult = true; _success = true; continue; }
            if (raw.StartsWith("❌")) { _hasResult = true; continue; }

            var m = LineRegex.Match(raw);
            if (!m.Success) continue;

            _entries.Add(new Entry
            {
                path = m.Groups[1].Value.Replace('\\', '/'),
                line = int.Parse(m.Groups[2].Value),
                isError = m.Groups[3].Value == "error",
                text = raw
            });
        }

        Repaint();
    }

    private static void Jump(Entry e)
    {
        var asset = AssetDatabase.LoadAssetAtPath<Object>(e.path);
        if (asset != null)
            AssetDatabase.OpenAsset(asset, e.line);
        else
            Debug.LogWarning($"[CompileResult] 파일 없음: {e.path}");
    }
}
#endif
