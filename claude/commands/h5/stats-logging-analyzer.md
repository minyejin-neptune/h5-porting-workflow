---
description: Stats Logging 분석 — 여러 프로젝트의 agent-stats.md를 대조해 3회 이상 반복 Zero-Hit 패턴을 찾아 보고한다
---

# Stats Logging 분석

여러 게임 프로젝트에 흩어진 `Docs/porting/.stats/agent-stats.md`를 모아, 같은 (에이전트, 라벨) 조합이 **Zero-Hit으로 3회 이상** 반복되는지 찾는다. 기록(쓰기)은 각 analyzer 에이전트가 자체적으로 담당한다 — 이 스킬은 **읽기·분석 전용**이다.

`$ARGUMENTS`로 특정 에이전트만 좁힐 수 있다(예: `iaa-analyzer`). 생략하면 전체 에이전트 대상.

추론 금지. 라벨은 **정확히 일치**하는 문자열만 집계한다 — 표현이 살짝 다른 라벨(예: "ShowRewardAD/ShowRewardedAd" vs "ShowRewardAD / ShowRewardedAd")은 자동으로 합치지 않는다. 근사 중복은 보고서에 나열만 하고, 사람이 육안으로 판단한다.

---

## STEP 1 — 프로젝트 stats 파일 탐지

경로를 하드코딩하지 않는다 — `find`로 자동 탐지한다.

```bash
find ~/github -maxdepth 4 -path "*/Docs/porting/.stats/agent-stats.md" 2>/dev/null
```

결과가 0건이면 "분석할 stats 파일이 없습니다"를 출력하고 종료한다.

## STEP 2 — 각 파일 Read 후 Zero-Hit Patterns 열 파싱

찾은 파일을 전부 Read한다. 각 행(`| Date | Agent | Hit Patterns | Zero-Hit Patterns |`)에서:
- `$ARGUMENTS`가 있으면 Agent 열이 그 값과 일치하는 행만 사용
- Zero-Hit Patterns 열을 콤마(`,`)로 split, 앞뒤 공백 제거
- (Agent, 라벨, 출처 프로젝트, Date)를 누적

## STEP 3 — (에이전트, 라벨)별 집계

같은 Agent + 정확히 동일한 라벨 문자열의 등장 횟수를 센다.

**3회 이상**인 조합만 추린다.

## STEP 4 — 보고

```
📊 Stats Logging 분석 — N개 프로젝트 대조

⚠️ 3회 이상 반복 Zero-Hit (재검토 후보)

[{agent-name}]
- "{라벨}" — N회
  · {프로젝트명} ({날짜})
  · {프로젝트명} ({날짜})
  ...

...
```

3회 이상인 게 없으면 "3회 이상 반복 Zero-Hit 없음 — 재검토 대상 없음"만 출력하고 종료한다.

## STEP 5 — 이슈화 여부 확인

보고 후 AskUserQuestion으로 확인한다:

> "위 항목을 이슈로 등록할까요?"
> - 전부 등록 → 항목별로 `/common:create-issue`를 호출해 각각 이슈 생성. 제목: `[Task] {agent-name} — "{라벨}" 탐색 패턴 재검토`, 본문에 반복 근거(프로젝트·날짜 목록)를 그대로 포함
> - 골라서 등록 → 등록할 항목을 다시 물어봄
> - 등록 안 함 → 보고만 하고 종료
