# content-analyze 일반화 — 설계 스펙

## 목적

`content-analyze` 스킬(`claude/commands/analyze/content-analyze.md`)을 **콘텐츠 종류에 무관하게** 동작하도록 일반화한다.

현재 문제 (근거: 실제 행 번호):
- 특정 프로젝트의 식별자가 grep에 하드코딩됨 — `IsOpen|IsUnlock|Menu_Is`(41,107행), `redDot|RedDot`(137행), `Board / GameManager`(120행), `GetContentsOpenTypes()`(173행), `MAX_*`(111행), `GameData*`(39행)
- 이 grep들에 **Zero-Hit Fallback이 없다** — 프로젝트 설정 감지 표(28~46행)에만 fallback이 있고, 분석 항목 안의 grep은 매칭 실패 시 5행의 일반 원칙에만 기댄다
- 분석 항목 1~6이 콘텐츠 종류와 무관하게 고정 적용됨
- 역기획서 원칙(85행: 코드·클래스명 배제)과 UI 구성 항목(133행: SerializeField 요소 목록)이 상충

---

## 핵심 설계 방향

### 1. porting-scan을 그대로 복제하지 않는다

porting-scan의 시스템 목록(IAP/광고/저장/랭킹 등)은 **모든 Unity WebGL 프로젝트에 보편적으로 존재**하므로 고정 행 스키마(`porting-scan.md:712-760`)가 성립한다.

"콘텐츠"는 게임마다 완전히 다른 자유 형식이므로 같은 방식으로 정형화하면 안 된다. **콘텐츠명을 입력받아 스캔이 동적으로 연관을 추적**한다.

### 2. 코드 참조 → 기획적 연관 번역

이 과제의 본질은 **코드의 참조관계를 기획적 콘텐츠 연관성으로 번역**하는 것이다.

"아무 코드 참조나 다 연관"으로 잡으면 두 가지가 깨진다:
- **노이즈** — 공통 Logger·Utils·베이스 UI 클래스 참조까지 전부 엣지가 됨
- **누락** — 기획상 진짜 연관이 직접 호출이 아니라 매니저·이벤트버스·공유 데이터 테이블 같은 간접 경로로만 이어지면 순수 호출관계로는 안 잡힘

→ "연관"은 아무 참조가 아니라 **정해진 관계 유형(엣지)으로 한정**한다. `content-analyze.md:115-129`(3번 연관 시스템)이 이미 쓰는 관계들을 귀납 출발점으로 삼는다. 각 유형은 grep/Read로 직접 검증 가능하므로 추론 금지 원칙을 지킨다. 코드에 연결이 전혀 없는 순수 기획적 연관은 그래프로 잡지 못하므로 `확인 필요`로 남긴다.

### 3. 매핑 규칙이 먼저, 산출물(그래프)은 그 다음

```
[관계 유형 매핑 규칙]   어떤 코드 근거 유형 = 어떤 기획 관계인가  (스키마)
        ↓ 엣지 유형 확정
[content-scan]         규칙대로 콘텐츠 연관 그래프 생성          (데이터)
        ↓ 산출물 소비
[content-analyze]      그래프를 참조해 문서 작성
```

매핑 규칙 = 스키마, 스캔 산출물 = 그 스키마로 채운 데이터. 따라서 **매핑 규칙 정의가 산출물 스펙보다 선행**한다.

### 4. 산출물을 파일로 남기는 이유 = 재실행 멱등성

porting에서 VOCAB이 막아주는 실패 모드("재실행 시 같은 탐색 반복 + 매번 다른 근거에 착지")가 기획서 쪽에도 그대로 있다:
- 문서 3개(역기획서·작업가이드·단계출시검토)가 같은 분석 결과를 소비 — `--docs`를 나눠 돌리면 매번 처음부터 재탐색
- STEP 2 spot-check → STEP 3 수정 루프도 원본 위치를 다시 찾아야 함
- 역기획서 누락 발견 후 재분석 시 기록이 없으면 전체 재탐색

→ content-scan 그래프 산출물이 이 역할(콘텐츠판 VOCAB)을 한다. **존재 이유는 PORTING_VOCAB과 동일 맥락**이나 형태·수명은 분리한다:

| | PORTING_VOCAB | 콘텐츠 연관 그래프 |
|---|---|---|
| 단위 | 프로젝트당 1개 | **콘텐츠당 1개** |
| 스키마 | 고정 행 | 관계 유형(엣지) 기반 자유 형태 |
| 수명 | 포팅 수명 내내 | 콘텐츠 코드 변경 시 낡음 → **신선도 판정 필요** |

> 프로젝트 설정(SCRIPTS_PATH, DATA_DECODE_CMD 등)은 PORTING_VOCAB이 있으면 재활용한다(`content-analyze.md:32` 방식). "프로젝트 설정 VOCAB"은 편의 입력이고, "콘텐츠 연관 그래프"는 매핑 규칙의 산출물이지 선행 조건이 아니다.

---

## Phase 진행 현황

> 각 Phase = GitHub 이슈 1개. 이슈가 닫히면 아래 체크박스를 갱신한다.

- [x] **Phase 1 — 관계 유형 매핑 규칙 정의** ([#56](https://github.com/minyejin-neptune/h5-porting-workflow/issues/56), closed)
  코드 참조 → 기획 연관 번역 규칙(엣지 스키마) + 제외 규칙 + `확인 필요` 경계. 파일럿(`infiniteranch-h5-client`/Skill) 귀납으로 관계 유형 10종 확정. 산출물: [`content-relation-mapping-rules.md`](./content-relation-mapping-rules.md). 신규 발견 카테고리(H·I·J)는 Phase 4에서 재검증 예정.
- [x] **Phase 2 — content-scan 스킬 구축** ([#57](https://github.com/minyejin-neptune/h5-porting-workflow/issues/57), closed)
  신규 [`claude/commands/analyze/content-scan.md`](../claude/commands/analyze/content-scan.md) (`analyze:content-scan`). 콘텐츠명 기반 동적 노드 추출 → Read 참조 추적 확장(Phase 1 매핑 규칙 그대로 참조) → 그래프 저장 + 신선도 판정(sdk-list-analyzer 방식). 실제 동작 검증은 Phase 4에서.
- [x] **Phase 3 — content-analyze 개편** ([#58](https://github.com/minyejin-neptune/h5-porting-workflow/issues/58), closed)
  그래프 참조 구조 전환(하드코딩 grep 제거·멱등성 게이트, 재확인 완료), SerializeField 원칙 충돌 해소, 분석 항목 1~6을 `[공통]`/`[조건부]`로 태깅(고정 타입명 대신 그래프·문서 존재 여부로 판정), STEP 1을 `effort: max`로 호출. 미해결: 레드닷이 A~J 카테고리에 안 맞음(Phase 1 addendum 후보).
- [x] **Phase 4 — 통합 검증** ([#59](https://github.com/minyejin-neptune/h5-porting-workflow/issues/59), closed)
  `infiniteranch-h5-client`의 Pet·Trophy로 dry-run — 5개 검증 포인트(하드코딩 부재·근거 정합·멱등성·신선도·역기획서 원칙 준수) 전부 통과. 발견사항을 `content-relation-mapping-rules.md`에 반영(H 방향성 구분, I·J 일반화 확인). K 카테고리(알림 뱃지) 신설은 후속 작업.

**Phase 간 의존**: `Phase 1 → Phase 2 → Phase 3 → Phase 4` (순차 필수) — **전체 완료**

---

## 후속 작업

- [x] **K 카테고리 신설** ([#60](https://github.com/minyejin-neptune/h5-porting-workflow/issues/60), closed): 알림 뱃지 연동 카테고리 추가 완료 — `content-relation-mapping-rules.md`·`content-scan.md`·`content-analyze.md` 3개 파일 모두 반영
- [x] **Agent 도구 effort 파라미터 오류 수정**: content-analyze.md STEP1의 "Agent 도구로 effort:max 호출" 지시가 실행 불가능했음(Agent 도구엔 effort 파라미터 없음 — Workflow의 agent() 전용). frontmatter 기반 안내로 수정 완료(#58 보강 코멘트, 커밋 `fd79cf6`)
- [x] **H 카테고리 방향 표기 모호성**: 화살표 관례를 "읽는 방향"에서 표준("영향이 흘러가는 방향")으로 통일 — 브랜치 `fix-h-category-direction`(워크트리)에서 수정, `content-analyze-generalize` 브랜치에 파일 복사 반영. 블라인드 재검증(별도 서브에이전트, 배경지식 없이 정의문+그래프 한 줄만 제공)에서 H-B/방향을 한 번에 정확히 판정 — 이전엔 "확인 필요"로 막혔던 지점이 해소됨을 실측 확인. 박물관 그래프의 H 표기도 새 관례로 갱신 완료
- [x] **미분류 강한 연관 `[신규후보]` 캡처 메커니즘**: A~K는 닫힌 분류 체계가 아닌데 STEP3가 안 맞는 관계를 그냥 버리는 구조였음(박물관 dry-run에서 GPGS 업적 연동을 통째로 놓친 근본 원인 — K 카테고리 부재가 아니라 "미분류 처리 규칙 자체의 부재"였음, 사용자 지적). 브랜치 `add-unclassified-category-capture`(워크트리)에서 STEP3에 `[신규후보]` 기록 규칙 추가, content-analyze도 누락 없이 반영, mapping-rules.md에 신규후보→정식 카테고리 승격 절차 명문화. 블라인드 재검증(GPGS 업적 호출부만 제공)에서 정확히 `[신규후보]`로 포착 확인
- 3문서(역기획서/작업가이드/단계출시검토) 개별 스킬 분리 + 상위 오케스트레이터 스킬 (사용자 보류, 남은 유일한 범위 밖 항목)

---

## 확정된 결정

- [x] 새 스캔 스킬 이름 — `content-scan` (`analyze:content-scan`)
- [x] porting-scan식 고정 행 스키마를 쓰지 않고 **콘텐츠 연관 그래프**를 동적 생성
- [x] "연관" = 정해진 관계 유형(엣지)으로 한정, `content-analyze.md:115-129`가 귀납 출발점
- [x] 매핑 규칙 정의가 산출물 스펙에 선행
- [x] 산출물은 **콘텐츠당 1개** 파일로 저장 (재실행 멱등성), 신선도 판정 포함
- [x] content-scan 모델 — `sonnet`, effort 기본값 (grep + Read 확인 위주의 기계적 탐색)
- [x] content-analyze 분석·문서 작성 단계 모델 — `sonnet`, `effort=max` (기획자 관점 서술·해석 판단이 몰림)
- [x] **카테고리 일반화 원칙**: 관계 유형(엣지)은 "조건 함수 참조", "데이터 테이블 컬럼 참조", "UI 팝업 트리거", "로그 이벤트 호출" 같은 Unity/C# 구조 패턴 레벨의 **카테고리**로만 정의한다. 실제 함수·클래스명(`SendLog`, `PopupManager.Add` 등)은 규칙에 넣지 않는다 — 그건 content-scan이 콘텐츠·프로젝트마다 매번 새로 동적 탐색한다(하드코딩 금지). 재분석 시 "매번 동적 탐색"은 같은 콘텐츠 재실행이 아니라 **새 콘텐츠·새 프로젝트를 처음 스캔할 때**만 해당 — 같은 콘텐츠는 저장된 그래프를 재사용(재실행 멱등성)
- [x] **파일럿 대상**: `/Users/admin/github/infiniteranch-h5-client` — `Assets/Scripts/Skill`(스킬 콘텐츠). content-analyze.md:116("스킬/능력치 테이블 연결 여부")과 직접 대응. 파일럿의 역할은 "이 프로젝트 실명을 규칙에 박기"가 아니라 "카테고리 분류가 실제 코드에서 말이 되는지" 확인하는 sanity-check — 이 프로젝트 특유의 구조에 과하게 의존한다고 판단되는 카테고리는 `[확인 필요]`로 표기해 Phase 4에서 다른 콘텐츠로 재검증
- [x] 그래프 산출물 경로 — `Docs/design/{콘텐츠명}/` (기존 역기획서 경로와 동일 폴더)
- [x] 그래프 산출물 형식 — 마크다운 중첩 목록(노드 아래 연관 노드를 들여쓰기로 표현), 표 형식 아님
- [x] 신선도 판정 기준 — porting-scan의 sdk-list-analyzer 방식과 동일 (기준 커밋 대비 관련 파일 변경 0건이면 재사용, 있으면 재생성)

## 미확정 → 전부 확정됨

- [x] 관계 유형(엣지) 최종 목록 — Phase 1 파일럿(Skill)으로 확정 → Phase 4(Pet·Trophy)로 재검증 완료
- [x] 공통 참조 제외 규칙의 판정 임계값 — Phase 1 파일럿으로 확정
- [x] 콘텐츠 타입 분류 체계 — 고정 타입명 대신 그래프·문서 존재 여부 기반 `[공통]`/`[조건부]` 태깅으로 Phase 3에서 확정

---

## 범위 밖 (보류 — 후속 작업 절 참고)

- 역기획서/작업가이드/단계출시검토 3개 문서를 개별 스킬로 분리 + 상위 오케스트레이터 스킬 설계
- 3종 이상 회귀 스위트 확대, 자동화 회귀 테스트 스크립트화
