# UID / version — 표시 위치 확정

원본: `claude/agents/porting/platform-porter.md` 13단계. **기존 방치 버그 항목** — h5-port STEP 3-A 사전 질문 표에 이 항목이 없어서 재질문 경로 자체가 없이 체크리스트에만 쌓이던 항목이다. 이 스킬이 최초로 실제 질문 경로를 갖는다.

**완료 신호**: `HLSDK.Instance.GetUserKey()` 호출 이미 존재 → 스킵.

**탐색**: VOCAB `{UID_VERSION_FILE}` → Read → grep fallback

```bash
# 버전/빌드 정보 표시 위치
grep -rn "version\|Version\|buildNumber\|AppVersion" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane | grep -iv "//.*version"

# UID 표시 위치
grep -rn "uid\|userId\|UserID\|GetUserKey\|userKey" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

탐색 결과로 분기한다:

- **기존 표시 UI가 있음** → 해당 UI에 `#if UNITY_WEBGL` 분기로 HLSDK 값(`HLSDK.Instance.GetUserKey()`) 표시하고 바로 진행(판단 불필요, 기계적으로 처리).
- **기존 표시 UI가 없음** → **AskUserQuestion으로 확정**: "UID/version을 표시할 기존 UI가 없습니다 — 어느 화면에 추가할까요?" (예: 설정 화면, 타이틀 화면 등 후보 제시 + "직접 지정"). 확정되면 그 위치에 구현. 미확정이면 `platform-checklist.md` `## 확인 필요`에 "UID/version 표시 위치 확인 필요" 기록하고 스킵.

> **코드 패턴**: `$H5PW_ROOT/templates/porter-patterns/platform-patterns.md` → "13. UID / version 추가"
