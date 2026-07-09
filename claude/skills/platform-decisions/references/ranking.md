# 랭킹 접근 버튼 — 신규 위치 확정

원본: `claude/agents/porting/platform-porter.md` 10-1단계. **10-2(랭킹 보드 연동)·10-3(점수 등록)·10-4(LIVE 분기)는 판단이 필요 없는 자동 스텝이라 platform-porter가 그대로 담당한다** — 이 스킬은 10-1(버튼 신규 위치)만 다룬다.

**완료 신호**: 랭킹 버튼 오브젝트에 `#if UNITY_WEBGL` 표시 분기 이미 존재 → 스킵.

**탐색**: VOCAB `{RANKING_FILE}` → Read → grep fallback

```bash
grep -rn "OpenLeaderBoard\|LeaderBoard\|Leaderboard\|RankButton\|OnClickRank" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

탐색 결과로 분기한다:

- **기존 버튼 있음(grep 히트)** → `HLSDK.Instance.OpenLeaderBoard()` 연결(판단 불필요, 기계적으로 처리). 완료 후 platform-porter가 10-2~10-4를 이어서 처리하도록 체크리스트에 기록.
- **신규 추가 필요(0건)** → `platform-checklist.md` `## 확인 필요`에서 **랭킹 버튼 위치** 기존 확정값이 있으면 그 값 사용. 없으면 **AskUserQuestion으로 확정**: "랭킹 버튼을 신규로 추가해야 합니다 — 어느 화면·클래스에 넣을까요?" (기존 UI 관리 클래스 목록 후보 제시 + "직접 지정" 선택지). 확정되면 그 위치에 구현(기존 UI 관리 클래스에 삽입 또는 별도 버튼 오브젝트 + 클릭 핸들러).

> 특정 플랫폼에서만 숨겨야 한다는 사실이 확인되면(예: 그 플랫폼이 `OpenLeaderBoardAsync`를 no-op으로 구현) 위 분기를 좁힌다 — 개별 플랫폼 포터가 필요 시 조정.

> **코드 패턴**: `~/github/h5-porting-workflow/templates/porter-patterns/platform-patterns.md` → "10-1. 랭킹 접근 버튼 확인"

## 처리 후

`platform-checklist.md` `## 단계 진행`의 `10-1. 랭킹 접근 버튼 확인`을 완료 처리하고, 10-2~10-4가 아직 미완료(`- [ ]`)면 "platform-porter 재실행으로 10-2~10-4 이어서 처리 필요"를 안내한다.
