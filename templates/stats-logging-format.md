# Stats Logging 공통 형식

grep 기반 탐색 에이전트/스킬이 프로젝트마다 어떤 패턴이 맞고(Hit) 어떤 패턴이 헛되게(Zero-Hit) 반복되는지 누적 기록해, 여러 프로젝트를 거치며 탐색 방법을 학습하기 위한 로그.

이 파일은 형식만 정의한다. **어떤 패턴을 추적할지(라벨 목록)는 각 에이전트/스킬 문서 자신의 "Stats Logging" 섹션에 남긴다** — 라벨은 그 문서가 실제로 실행하는 grep과 1:1이라 여기서 대신 정의하면 드리프트가 생긴다.

## 저장 위치

`Docs/porting/.stats/agent-stats.md` — 산출물 저장 완료 후 한 행을 추가한다. 디렉토리가 없으면 `mkdir -p Docs/porting/.stats`로 먼저 생성한다. 파일이 없으면 헤더와 함께 생성한다.

## 헤더 (최초 1회)

```
| Date | Agent | Hit Patterns | Zero-Hit Patterns |
|---|---|---|---|
```

## 행 형식

```
| YYYY-MM-DD | {agent-name} | label_a(N건), label_b(N건) | label_c, label_d |
```

`{agent-name}`은 호출한 에이전트/스킬 이름(예: `iap-analyzer`, `porting-scan`)을 그대로 쓴다.

## 패턴 정리 기준

같은 라벨이 여러 프로젝트에서 Zero-Hit으로 **3회 이상** 누적되면, 해당 라벨의 탐색 방법을 원 문서에서 재검토할 후보로 삼는다. 이 정리는 자동 실행되지 않는다 — 유지보수 세션에서 `.stats/agent-stats.md`를 읽고 판단한다.
