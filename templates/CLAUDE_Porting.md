# CLAUDE.md

## Rules (strictly enforced)

### Response Rules
- **Always respond in Korean** in chat, regardless of the language used in instructions or code.
- Before any code analysis response, ask the user to choose the output format (save as `.md` file / print in chat).
    - If `.md` file is chosen: save to the `.md/` subfolder inside the folder containing the target class. Do NOT duplicate output in chat. (e.g., `Assets/500_Scripts/PlayManager/.md/bug-xxx.md`)
    - If chat is chosen: print directly in chat.
- Do NOT delete original comments. If deletion is necessary, always ask first.
- **No inference**: Only present facts confirmed by directly reading the code. Do not assert causes using speculative expressions like "it is likely that~" or "it may be because~". If no evidence is found in the code, explicitly state "코드에서 근거를 찾지 못했습니다".
- **Insufficient data**: If the information needed to make a judgment is not present in the code, explicitly state "insufficient data".

---

## Project-Specific Settings (filled during porting-init — confirm from code; delete any line that does not apply)

### Project Summary
Fill with a one-line description (e.g. Unity mobile game, Toss/PureWeb WebGL build target).
Details: [.md/PROJECT.md](.md/PROJECT.md)

### Custom Build Entry Point (project-only, beyond HyperLane `Hyperlane/Build/`)
- e.g. `Treeplla/Build/` (`Assets/Treeplla/Editor/AutoBuild.cs`) — delete if not present.

### Deploy Command
- e.g. `cd Deploy/Toss/unity-webgl-wrapper && ./deploy-ait.sh` — replace with the actual path, or delete if none.

### Project-Only Define Symbols (beyond the standard `WEBGL_*`)
- e.g. `AVOEX_FIREBASE` (Firebase), `AVOEX_CLOUD_ONCE` (CloudOnce) — list only what the project actually uses; confirm prefix and name from code.

---

## Pre-Analysis Reference

Before any code analysis, check if the following files exist and read them first.
Do not re-analyze content already documented there.

| File | Purpose |
|---|---|
| `Docs/FRAMEWORK_REFERENCE.md` | Entry points, systems, utilities, helpers, reusable APIs — read before any code exploration |
| `Docs/porting/PORTING_ANALYSIS.md` | SDK list, compile/runtime issues |
| `Docs/porting/PORTING_VOCAB.md` | Method/class vocabulary — check before grepping |

After completing analysis of any game system, check the relevant doc in `Docs/`.
If the doc is outdated or contradicts the code — update it and report what changed.

---

## Excluded from Analysis / Modification

### Internal Company SDK — No modification / Request permission before reading

| Path | Rule |
|---|---|
| `Assets/HyperLane/` | No code modification. **If reading (Read/grep) is needed, request permission via AskUserQuestion first.** |

- Modification (Edit/Write) is forbidden under any circumstances.
- Reading (Read/grep) is allowed only after permission is granted, for the purpose of understanding the API.
- Do not read automatically without permission.

---

## Verification Rules

- **Never state a count, enum list, or logic conclusion** without first verifying it from the actual code. Show the exact command and output used as evidence.
- Before concluding that something "does not exist," run an exhaustive search (grep/find) and show the search commands.
- This strengthens the existing No Inference rule: no speculative expressions, no guesses dressed as facts.

---

## Code Modification Rules

- **Prefer reusing existing public methods** over editing internal keys or values directly (e.g., use `PopupManager.ShowAlertAsync` instead of editing popup key strings).
- Before modifying shared/global variables or prefixes: check all usages first. If the variable is reused elsewhere, introduce a new one instead.

---

## General Coding Rules

- Do not delete existing code — wrap it in preprocessor directives (`#if`) instead. Existing code without a preprocessor directive should be wrapped in `#if !UNITY_WEBGL` by default.
- No column alignment in variable declarations — do not use space padding to vertically align types/names.
- After completing porting-related code changes (WebGL preprocessors, SDK handling, compile/runtime issue fixes): update `Docs/porting/PORTING_ANALYSIS.md` status columns. If a method name or file path was newly confirmed, add it to `Docs/porting/PORTING_VOCAB.md` as well.
- After completing each porting task, run compile check before committing (Unity menu **Tools/H5/Compile Check**, or batch mode `CompileChecker.Run`).

---

## Git Branch Workflow

### worktree — required for parallel work on branches sharing the same HEAD

**Always separate directories using worktree, or stack commits on each branch before switching.**

```bash
# Create a new worktree (with a new branch)
git worktree add ../{project-name}-<suffix> -b <branch-name>

# List worktrees
git worktree list

# Remove after work is done
git worktree remove ../{project-name}-<suffix>
```

### Commit Message Prefix

커밋 메시지는 `[prefix] 내용` 형식을 사용한다.

| Prefix | 용도 |
|---|---|
| `[토스]` | Toss 플랫폼 관련 |
| `[퓨어웹]` | PureWeb 플랫폼 관련 |
| `[웹지엘]` | WebGL 공통 관련 |
| `[공통]` | 플랫폼 무관 공통 변경 |
| `[수정]` | 버그 수정 |
| `[문서]` | 문서 작업 |
| `[빌드]` | 빌드 설정 |

---

### Separating mixed changes into different branches

If changes are already mixed on the same branch — before committing:

1. Commit on the current branch first (to diverge the branch HEAD).
2. `git checkout <target-branch>` — files are now separated.
3. Manually apply only the target files, then commit.

---

## Build / Deploy Rules

- Builds must be run only from Unity Editor menu `Hyperlane/Build/`.
- For project-only build menus and deploy commands, see **"Project-Specific Settings"** at the top.
- Follow the required define combinations per platform:

| Build Target | Required Define Symbols |
|---|---|
| Toss DEV | `WEBGL_TOSS`, `WEBGL_DEV_VER`, `ENABLE_LOG`, `WEBGL_DEBUG_CONSOLE` |
| Toss LIVE | `WEBGL_TOSS`, `WEBGL_LIVE_VER` |
| Pure DEV | `WEBGL_PUREWEB`, `WEBGL_DEV_VER`, `ENABLE_LOG`, `WEBGL_DEBUG_CONSOLE` |
| Pure LIVE | `WEBGL_PUREWEB`, `WEBGL_LIVE_VER` |

### Define Symbol Reference

| Symbol | Meaning |
|---|---|
| `WEBGL_TOSS` | Toss platform build |
| `WEBGL_PUREWEB` | Standalone WebGL build |
| `WEBGL_DEV_VER` | Development build |
| `WEBGL_LIVE_VER` | Production build |
| `ENABLE_LOG` | Enable debug logging |
| `WEBGL_DEBUG_CONSOLE` | Enable on-screen debug console |

> For project-only defines (Firebase, save SDK, etc.), see **"Project-Specific Settings"** at the top.

---

## Scope & Approval Rules

- **Do not create new files** without explicit user confirmation. Propose the file name and purpose first, wait for approval.
- **Do not expand scope** beyond what was requested — no new controllers, features, or refactors unless asked.
- Before editing shared/global variables or prefixes (e.g., promotion prefixes, manifest entries): verify they are not reused elsewhere. Prefer introducing a new variable over modifying the existing one.
- If unsure whether a change is in scope, stop and ask.

---

## Documentation Rules

### Target Audience & Location — strictly distinguish

| Type | Location | Audience | Rule |
|---|---|---|---|
| 역기획서 (design doc) | `Docs/design/` (per-system subfolders) | Planner | No raw code dumps. Explain mechanics in plain language only. |
| 개발 작업 가이드 (dev guide) | `Docs/FRAMEWORK_REFERENCE.md` | Developer | Implementation notes allowed (e.g., 0-based index, API names). |
| Porting artifacts | `Docs/porting/` | Workflow | PORTING_ANALYSIS, VOCAB, checklist, logs, porting notes |
| Content definitions | `Docs/design/contents/` | Planner | Unlock conditions, values |

- Never mix types: index/API notes belong in the dev guide, not the 역기획서.
- When creating a new doc, confirm its type and save location with the user.
- Save all documentation under `Docs/`. **But if the project already has a different doc structure, follow that structure.**
