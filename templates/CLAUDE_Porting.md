# CLAUDE.md

## Rules (strictly enforced)

### Response Rules
- **Always respond in Korean** in chat, regardless of the language used in instructions or code.
- Before any code analysis response, ask the user to choose the output format (save as `.md` file / print in chat).
    - If `.md` file is chosen: always ask the user where to save it — never assume a default location. Do NOT duplicate output in chat.
    - If chat is chosen: print directly in chat.
- **No inference**: Only present facts confirmed by directly reading the code. Do not assert causes using speculative expressions like "it is likely that~" or "it may be because~". If no evidence is found in the code, explicitly state "코드에서 근거를 찾지 못했습니다".
    - **Never state a count, enum list, or logic conclusion** without first verifying it from the actual code. Show the exact command and output used as evidence.
    - Before concluding that something "does not exist," run an exhaustive search (grep/find) and show the search commands.
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

## Porting Workflow Overview

When a request is porting-related, follow this order — proactively suggest it even if the user doesn't spell out each step.

1. For a new porting session, start with `h5-port` — it runs STEP 0–4 (encoding fix, `porting-scan`, `porting-scan-verify`, porter execution, `porting-verify` final check) in sequence automatically. If the user asks for a specific step only, jump straight there (e.g., "redo just the porter" → STEP 3).
2. After modifying porting-related code, verify with the `porting-verify` skill before committing (it owns interpreting the result — `❌ 미처리` / `⚠️ 확인 필요` / `✅ 이상 없음` — plus exceptions handling) — do not run `h5-port-verify.py` directly.
3. If `platform-checklist.md` `## 단계 진행` shows `⏭️ 스킵: /platform-decisions ...로 처리 필요`, or the user asks directly about haptics, ranking button, share text, UID/version, unnecessary-UI removal, or localization, run the `platform-decisions` skill (no argument shows what's pending) — platform-porter (a subagent) can't ask these questions itself, which is why they're split out.
4. If h5-port's completion report lists pending judgment items, suggest running `platform-decisions` right away without waiting to be asked.

---

## Pre-Analysis Reference

Before any code analysis, check if the following files exist and read them first.
Do not re-analyze content already documented there.

| File | Purpose |
|---|---|
| `Docs/FRAMEWORK_REFERENCE.md` | Entry points, systems, utilities, helpers, reusable APIs — read before any code exploration |
| `Docs/porting/NATIVE_BASELINE.md` | Pre-porting native snapshot (immutable) — SDK inventory, project info, game structure |
| `Docs/porting/pureweb-checklist.md` | Work list (mutable) — compile/runtime/void issues, status |
| `Docs/porting/PORTING_VOCAB.md` | Method/class vocabulary (location index) — check before grepping |

After completing analysis of any game system, check the relevant doc in `Docs/`.
If the doc is outdated or contradicts the code — update it and report what changed.

### Code Search Rule — VOCAB first

When looking for a file, class, or method, always follow this order. Actively use VOCAB (the location index).

1. Check the item's file:line in `Docs/porting/PORTING_VOCAB.md` first — if present, Read it directly (no grep).
2. If the row is missing or marked "확인 필요" → grep/find fallback.
3. If the grep/find fallback also finds nothing and this step has no already-specified handling (e.g., skip) — do not guess. Record it in the project's checklist `## 확인 필요` section for human review, and move to the next step.
4. Add any file:line newly confirmed via grep fallback to VOCAB `## 포터 기록`, so it is never re-searched.

Do not use grep as the **first** resort — if VOCAB has the answer, use it. (Before concluding something "does not exist", follow the exhaustive-search rule in Verification Rules below.)

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

## Code Modification Rules

- **Prefer reusing existing public methods** over editing internal keys or values directly (e.g., use `PopupManager.ShowAlertAsync` instead of editing popup key strings).
- Before modifying shared/global variables or prefixes: check all usages first. If the variable is reused elsewhere, introduce a new one instead.

---

## General Coding Rules

- Do NOT delete original comments. If deletion is necessary, always ask first.
- **After changing code, always update the affected docs** (dead-document prevention) — checklist, VOCAB, FRAMEWORK_REFERENCE, design docs, whichever the change touches.
- No column alignment in variable declarations — do not use space padding to vertically align types/names.
- Prefer explicit types over `var`.
- **Compress step-transition reports to 2–3 lines** (✅/⏳ markers) — put full detail in the checklist/VOCAB doc, not the chat.
- **List-type results (e.g. compile errors): show a count + at most 3 representative items** in chat; write the full list to the checklist `## 이슈`.
- **Skip filler progress messages** (e.g. "확인 중입니다", "잠시만 기다려주세요") — report only the result.
- **When quoting a subagent's completion report, extract only the essentials** (scope done, error count, `## 확인 필요` items) — do not re-paste the full report.

---

## Porting Behavior Rules

- Do not delete existing code — wrap it in preprocessor directives (`#if`) instead. Existing code without a preprocessor directive should be wrapped in `#if !UNITY_WEBGL` by default.
- **Porting must not change which branch existing define combinations take** (editor shadowing invariant). In the editor with WebGL build target, `UNITY_EDITOR` and `UNITY_WEBGL` are both defined — when inserting a new WebGL arm in front of a chain that mentions `UNITY_EDITOR` below, add `&& !UNITY_EDITOR` to the new arm.
- Porter subagents (pureweb/platform/toss-porter) follow their own operational procedure (decision-routing, checklist/VOCAB updates, compile checks, verification) as defined in `porter-rule.md` — do not duplicate it here. For platform-porter's 6 judgment steps (haptic, ranking button, share text, UID/version placement, unnecessary-UI removal, localization) that it can't resolve on its own, run the `platform-decisions` skill.

---

## Task Workflow (Plan → Issue → Resolve)

Progress large tasks in the following order.

1. `/common:feature-breakdown <problem>` — break the task down into executable subtasks.
2. `/common:create-issue <content>` — turn the subtasks into GitHub issues.
3. `/common:resolve-issue <issue-number>` — fetch the issue, plan the fix, and resolve it.

- **Required**: If any change arises before the issue is resolved (scope change, design change, etc.), you MUST update the plan document or the issue FIRST, then proceed. Never proceed while the code and the plan/issue are out of sync.

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
| Porting artifacts | `Docs/porting/` | Workflow | NATIVE_BASELINE, VOCAB, pureweb/toss-checklist, logs, porting notes |
| Content definitions | `Docs/design/contents/` | Planner | Unlock conditions, values |

- Never mix types: index/API notes belong in the dev guide, not the 역기획서.
- When creating a new doc, confirm its type and save location with the user.
- Save all documentation under `Docs/`. **But if the project already has a different doc structure, follow that structure.**
