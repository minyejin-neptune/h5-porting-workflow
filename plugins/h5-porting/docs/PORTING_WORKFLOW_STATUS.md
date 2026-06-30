# H5 포팅 워크플로우 — 파일 인벤토리 & 완성도 평가

> 기준 문서: `/Users/admin/github/.templates/CLAUDE_Porting.md`
> 작성: 워크플로우 강화 세션 / 모든 평가는 실제 파일 Read·grep 근거. 미확인은 "미확인"으로 표기.
> 범례: 🟢 성숙(바로 사용 가능) · 🟡 보강 필요 · 🔴 결함/미흡

---

## 1. 파이프라인 한눈에

```
[프로젝트 셋업]  porting-init  → CLAUDE.md·README·Editor 툴 연결
       ↓
[오케스트레이터] h5-port  (STEP 0~4 전체 지휘)
   STEP 0  초기설정·브랜치·Addressables·커밋
   STEP 1  EUC-KR→UTF-8 / Android 컴파일 / hook / HLSDK 확인
   STEP 2  porting-scan → porting-scan-verify → 기획문서(iap/iaa/save) → 커밋
   STEP 2-E WebGL 컴파일 체크
   STEP 3  포터 실행 (toss-porter / pureweb-porter, subagent)
   STEP 4  h5-port-verify.py 최종 검증
```

산출물: `Docs/porting/PORTING_ANALYSIS.md`, `PORTING_VOCAB.md`, `Docs/design/*.md`

---

## 2. 파일 인벤토리 & 완성도

### A. 기준·규칙 문서

| 파일 | 줄수 | 역할 | 완성도 |
|---|---|---|---|
| `.templates/CLAUDE_Porting.md` | 173 | 프로젝트별 CLAUDE.md 원본(규칙·define·빌드·git) | 🟡 결함 1건 (아래 4-①) |
| `.templates/README.md` | 26 | Docs 폴더 구성 안내 | 🟢 |

### B. 오케스트레이션 (commands/)

| 파일 | 줄수 | 역할 | 완성도 |
|---|---|---|---|
| `commands/project/porting-init.md` | 83 | 템플릿 복사 + Editor 심볼릭 링크 | 🟢 |
| `commands/h5/h5-port.md` | 484 | 전체 오케스트레이터 (STEP 0~4) | 🟢 단계별 커밋·게이트·컴파일 체크 촘촘 |
| `commands/h5/porting-scan.md` | 857 | 사전 분석 (SDK/런타임/공백/게임구조) | 🟢 단, 커버리지 공백 2건 (4-③) |
| `commands/h5/porting-scan-verify.md` | 313 | 스캔 결과 7종 병렬 검증 | 🟢 |

### C. 포터 에이전트 (agents/porter/)

| 파일 | 줄수 | 역할 | 완성도 |
|---|---|---|---|
| `agents/porter/toss-porter.md` | ~2384 | Toss 포팅 16단계 | 🟡 1·2번 강화 적용됨 / 잔여 TODO·비대 |
| `agents/porter/pureweb-porter.md` | 1129 | PureWeb 포팅 | 🟡 VOCAB 게이트 없음·leak 스캔 미실시 |
| `.templates/h5-porter-template.md` | 261 | 신규 포터 작성 베이스 | 🟡 패턴 명명 불일치 (4-②) |

### D. 보조 에이전트 (agents/)

| 파일 | 줄수 | 역할 | 완성도 |
|---|---|---|---|
| `agents/unity-compile-checker.md` | 283 | Editor 로그 기반 컴파일 에러 자동 수정 | 🟢 |
| `agents/h5-game-porting-analyst.md` | 233 | 소스→역기획서, 버그 역추적 | 🟢 |
| `agents/toss-sdk-expert.md` | 43 | 앱인토스 SDK Q&A | 🟡 얇음·외부 문서 의존 |

### E. 스크립트·빌드 인프라 (.templates/)

| 파일 | 역할 | 완성도 |
|---|---|---|
| `.templates/scripts/h5-port-verify.py` | 994줄. 전처리 파서 + scan-void/scan-callers 모드 | 🟢 |
| `.templates/Editor/CompileChecker.cs` | 배치모드 컴파일 체크 진입점 | 🟢 (코드 상세 미확인) |
| `.templates/Editor/CompileResultWindow.cs` | 컴파일 결과 EditorWindow | 🟢 (코드 상세 미확인) |
| `.templates/Editor/TextureFormatSetter.cs` | WebGL 텍스쳐 포맷 일괄 설정 | 🟢 (코드 상세 미확인) |
| `.templates/Editor/HLAddressableTool.cs` | Addressables 원격화 툴 | 🟢 (코드 상세 미확인) |

### F. 기획 문서 생성기 (포팅 보조, 핵심 경로 아님)

`iap-analyzer` · `iaa-analyzer` · `save-point-analyzer` · `currency-analyzer` · `local-push-analyzer` · `biz-doc-writer` — STEP 2-C에서 병렬 호출. 본 평가 범위 밖(별도 영역).

### G. 산출물 (프로젝트별 생성, 정적 파일 아님)

`PORTING_ANALYSIS.md` · `PORTING_VOCAB.md` · `Docs/design/*.md` · `compile_result.log`
→ VOCAB 품질이 프로젝트마다 편차 큼 (luckysurvival 14줄 ↔ infiniteranch 78줄). 이미 toss-porter에 완전성 게이트로 방어.

---

## 3. 단계별 완성도 (포팅 파이프라인 기준)

| 단계 | 담당 파일 | 완성도 | 비고 |
|---|---|---|---|
| 초기 설정 | porting-init, CLAUDE_Porting | 🟢 | define 표 결함만 |
| 인코딩/환경 검증 | h5-port STEP 1 | 🟢 | |
| 사전 스캔 | porting-scan | 🟢 | 게임 로직·로그인로그 위치 미커버 |
| 스캔 검증 | porting-scan-verify | 🟢 | |
| 기획 문서 | analyzer 3종 | 🟢 | |
| 컴파일 체크 | CompileChecker + STEP 2-E | 🟢 | |
| **Toss 포팅** | toss-porter | 🟡 | 잔여 TODO 5건 (다른 세션 진행) |
| **PureWeb 포팅** | pureweb-porter | 🟡 | toss 강화 미반영 (비대칭) |
| 최종 검증 | h5-port-verify.py STEP 4 | 🟢 | |

**요약: 분석·검증·인프라 파이프라인(스캔→검증→컴파일→최종검증)은 성숙. 약한 고리는 "포터 2종"에 집중.**

---

## 4. 발견된 결함·불일치 (코드 근거)

**① CLAUDE_Porting.md define 표 오타** (🔴)
- 132줄: `Pure LIVE | WEBGL_PUREWEB, WEBGL_DEV_VER` → LIVE인데 `WEBGL_DEV_VER`. `WEBGL_LIVE_VER`이어야 함. 복사되는 원본이라 전 프로젝트에 전파됨.

**② 패턴 명명 불일치** (🟡, TODO 1·2와 직결)
- `h5-porter-template.md`: 패턴 A(플랫폼 전용) / B(플랫폼마다) — 2개 체계
- `toss-porter.md`: 패턴 A(HLSDK 공통=`UNITY_WEBGL`) / B(TossHandler 전용) / C(플랫폼마다) — 3개 체계, 의미 다름
- → 같은 "패턴 A"가 문서마다 다른 뜻. 포터가 "HLSDK 공통(패턴A)"을 "플랫폼별(패턴C)"로 오분류하는 TODO 1·2의 구조적 토양.

**③ porting-scan 커버리지 공백** (🟡, TODO 3·4와 직결)
- 로그인 로그(`LogDailyLogin`) **삽입 위치**(로비 진입 시점)를 VOCAB에 앵커로 안 잡음 → 포터가 grep 추측 (TODO 3).
- FeverUIManager류 게임 **로직 상태매니저** 탐지 항목 없음 (TODO 4).

**④ VOCAB 완전성 게이트 비대칭** (🟡)
- toss-porter: 게이트 있음(이번 세션 추가). pureweb-porter: **없음**. 같은 할루시네이션 위험이 PureWeb에 잔존.

---

## 5. 종합 평가 & 우선순위

**전체 완성도: 약 75% — "분석/검증/인프라는 거의 완성, 포터 2종이 미완".**

개선 우선순위 (영향도 ÷ 비용):

1. 🔴 **CLAUDE_Porting.md 132줄 define 오타** — 1줄, 즉시. 전파 중인 버그.
2. 🟡 **pureweb-porter 강화** — toss와 동일하게 VOCAB 게이트 + leak 스캔. 충돌 없음(다른 세션이 안 건드림).
3. 🟡 **패턴 명명 통일** — template ↔ toss-porter 패턴 체계 일치 (TODO 1·2 근본 토양). 단 toss-porter는 다른 세션이 쥠 → 조율 필요.
4. 🟡 **porting-scan 커버리지** — 로그인로그 위치·게임로직 항목 추가 (TODO 3·4). 큰 작업.

> TODO 1·2·5(toss-porter 내용 버그)는 다른 세션 진행 중 → 본 워크플로우 세션은 **1·2·4번(이 세션 단독 가능 영역)** 부터 손대는 게 충돌 없음.
