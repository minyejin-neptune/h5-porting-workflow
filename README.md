# h5-porting-workflow

Unity 모바일 게임을 **Toss / PureWeb WebGL(H5)** 로 포팅하는 Claude Code 워크플로우

- 배포 방식: **git clone + 심볼릭 링크** (플러그인 아님)
- 편집은 repo에서, `git pull`로 전 프로젝트에 즉시 반영

## 스킬 & 에이전트 구조

### 메인 파이프라인 — `/h5:h5-port` 하나로 오케스트레이션

```
/h5:h5-port (스킬, 오케스트레이터)
  → STEP 0  project:porting-init (스킬)        CLAUDE.md·FRAMEWORK_REFERENCE.md·HyperLane SDK 설치
  → STEP 1  EUC-KR → UTF-8 인코딩 변환           (h5-port가 직접 처리)
             ↳ sdk-list-analyzer (에이전트) 📊  외부 SDK 목록 — Android 컴파일 체크와 병렬 실행
  → STEP 2  h5:porting-scan (스킬) 📊
              → h5:porting-scan-verify (스킬)   NATIVE_BASELINE·VOCAB·체크리스트 생성 및 검증
  → STEP 3  pureweb-porter (에이전트)           SDK 초기화·로그인·저장·광고·IAP — 브라우저 테스트 가능
              → platform-porter (에이전트)      HLSDK 서버 연동 — Toss/Kakao 공통
                → toss-porter (에이전트)        Toss 전용 — 배너·프로모션 등
  → STEP 4  porting-verify (스킬)               플랫폼별 처리 누락 최종 검증
                                                (h5-port-verify.py 실행 + ❌/⚠️ 해석·exceptions 처리)

📊 = grep 탐색 결과를 대상 프로젝트의 Docs/porting/.stats/agent-stats.md 에 기록 (Hit/Zero-Hit 패턴 누적)
```

### 독립 실행 — 파이프라인 밖에서 필요할 때 직접 호출

```
analyze:content-scan (스킬) → analyze:content-analyze (스킬)
  content-scan   콘텐츠명으로 코드 참조를 추적 → {콘텐츠명}_연관그래프.md 생성
  content-analyze 그 연관그래프를 읽어 역기획서/작업가이드/단계출시 문서 생성

design:iap-analyzer / iaa-analyzer / save-point-analyzer (에이전트) 📊
  porting-scan 산출물(NATIVE_BASELINE·VOCAB) 재사용 → 사업팀 전달용 IAP/IAA/저장 역기획 문서

h5:stats-logging-analyzer (스킬)
  위 📊 지점들이 여러 프로젝트에 남긴 agent-stats.md를 전부 대조
  → 같은 (에이전트, 라벨)이 3회+ 반복 Zero-Hit → 탐색 패턴 재검토 후보로 보고 → 이슈화 제안

common:feature-breakdown → common:create-issue → common:resolve-issue (스킬 체인)
  이 워크플로우 자체를 수정할 때 쓰는 계획 → 이슈 → 구현 루틴
```

## 구조

```
claude/                       # ~/.claude 에 심볼릭될 내용
  agents/
    porting/    pureweb-porter, platform-porter, toss-porter, sdk-list-analyzer
    design/     iap-analyzer, iaa-analyzer, save-point-analyzer
  commands/
    h5/         h5-port, porting-scan, porting-scan-verify, stats-logging-analyzer
    project/    porting-init
    analyze/    content-scan, content-analyze
    common/     feature-breakdown, create-issue, resolve-issue, auto-resolve
  skills/
    platform-decisions/       # 사람 판단 이관 항목 처리 (+ references/ 6종)
    porting-verify/           # h5-port-verify.py 실행 + ❌/⚠️ 해석·exceptions 처리
templates/                    # 워크플로우가 repo 경로로 직접 참조 (심볼릭 없음)
  CLAUDE_Porting.md           # 게임 프로젝트 CLAUDE.md 원본 (porting-init이 복사)
  porter-rule.md              # 포터 3종 공용 규칙 단일 소스 + 새 포터 템플릿
  README.md                   # 산출물 전체 목록
  stats-logging-format.md     # agent-stats.md 기록 형식
  porter-patterns/            # 포터가 "코드 패턴" 포인터로 참조 — platform/pureweb/toss
  scripts/
    h5-port-verify.py         # CLI 진입점 (모드 dispatch)
    h5_port_verify/           # 검증 로직 패키지 (core, verify/shadow/void/callers_mode)
    compile-check.sh          # 컴파일 체크 — CLI 모드 + hook 모드 겸용
    worktree-setup.sh, hyperlane-init.sh, hyperlane-update.sh
  Editor/*.cs                 # porting-init이 게임 프로젝트로 복사
docs/
  기준-체크리스트.md           # 사람 수동 포팅 체크 표 — 워크플로우가 커버해야 하는 정답지
install.sh                    # $H5PW_ROOT 등록 + claude/·컴파일 체크 hook 심볼릭 연결
```

> **clone 위치는 자유, 폴더명만 고정**: 워크플로우가 `$H5PW_ROOT/templates/...`를 직접 참조하는데,
> `$H5PW_ROOT`는 `install.sh`가 실행 시점의 실제 clone 경로를 감지해 셸 rc에 등록해준다.
> 단 repo 폴더명은 반드시 **`h5-porting-workflow`**여야 한다 (문서들이 이 이름을 전제로 함).

## 설치 (각자 1회)

```bash
git clone https://github.com/minyejin-neptune/h5-porting-workflow.git ~/github/h5-porting-workflow
cd ~/github/h5-porting-workflow
./install.sh
```

`install.sh` 가 하는 일:
- `$H5PW_ROOT` 를 셸 rc에 등록 (실제 clone 경로 감지)
- `claude/` 의 모든 파일 → `~/.claude/` 에 심볼릭 (agents·commands·skills)
- `templates/scripts/compile-check.sh` → `~/.claude/hooks/compile-check.sh` 에 심볼릭 (컴파일 체크 hook)
- 기존 실제 파일이 있으면 `.bak` 으로 백업

> `templates/` 는 심볼릭하지 않는다. 워크플로우가 `$H5PW_ROOT/templates/` 를 직접 참조한다.
> 단 컴파일 체크 hook만 예외 — settings.json이 참조할 고정 경로가 필요해서 `~/.claude/hooks/` 로 건다.
> repo를 옮겨도 `install.sh` 재실행이면 링크가 갱신되므로 settings.json은 손대지 않아도 된다.

설치 후 Claude Code 재시작.

**컴파일 체크 hook 등록** (`.cs` 수정 시 자동 컴파일 검사 — 선택이지만 권장):
`~/.claude/settings.json` 의 `hooks.PostToolUse` 에 아래를 추가한다(기존 hook과 병합). `jq` 가 필요하다.

```json
{
  "matcher": "Edit|Write",
  "hooks": [
    { "type": "command", "command": "~/.claude/hooks/compile-check.sh" }
  ]
}
```

미등록 시엔 포팅 중 Unity 메뉴 **Tools/H5/Compile Check** 를 직접 실행해야 한다. `h5-port` STEP 1-B가 등록 여부를 확인하고 안내한다.

## 업데이트

```bash
cd $H5PW_ROOT && git pull
```
`~/.claude` 는 심볼릭이라 **재설치 없이** 즉시 반영. 템플릿(`templates/`)도 repo 실파일이라 pull하면 바로 최신.
단, 이미 포팅한 프로젝트에 **복사된** Editor 스크립트는 자동 갱신 안 됨(복사본) — 갱신하려면 porting-init 재실행 또는 수동 재복사.

## 처음 사용하기

1. [설치](#설치-각자-1회)를 최초 1회 진행한 뒤 Claude Code를 재시작한다.
2. 이 워크플로우 repo가 아니라 **포팅 대상 게임 프로젝트 폴더**에서 Claude Code를 실행한다.
3. `/h5:h5-port`를 실행하면 STEP 0~4 전체 파이프라인이 순서대로 진행된다. 플랫폼이 이미 정해져 있다면 `/h5:h5-port toss` 또는 `/h5:h5-port pureweb`로 바로 시작할 수 있다.
4. 진행 중 사람의 확인이 필요한 지점(HyperLane SDK 설치 여부, IAP PID 매핑 등)에서는 AskUserQuestion으로 그때그때 확인을 요청한다.
5. 포터의 완료 보고에 `⏭️ 스킵: /platform-decisions ...`가 표시되면, 해당 항목은 사람의 판단(햅틱·랭킹버튼·공유문구·UID/version·UI삭제·로컬라이제이션)이 필요해 이관된 것이다. `/platform-decisions`를 인자 없이 실행하면 대기 중인 항목 목록을 확인할 수 있다.
6. 완료 보고의 `🔍 수동 테스트 필요` 항목은 빌드 배포 후 브라우저에서 직접 확인해야 하는 항목이다.
7. 진행 상황 확인이나 문제 파악은 채팅 로그가 아니라 **`Docs/porting/{platform}-checklist.md`**를 기준으로 한다 — 이 파일이 정본이다(자세한 내용은 아래 "상태 관리" 참조).

```bash
/h5:h5-port            # 전체 오케스트레이터 (STEP 0~4)
/h5:h5-port toss        # 토스 포팅 바로 (pureweb-porter → platform-porter → toss-porter 순서로 자동 진행)
/h5:h5-port pureweb     # 퓨어웹만
/h5:porting-scan        # 사전 분석만
```

개별 포터를 직접 호출할 수도 있다(`Agent 도구, subagent_type: "pureweb-porter"` 등) — 이 경우 각 포터가 선행 포터 완료 여부를 진입점에서 스스로 확인하고, 안 됐으면 대신 실행하지 않고 안내만 한 뒤 반환한다.

막히면: `templates/README.md`(산출물 전체 목록), `docs/기준-체크리스트.md`(사람 수동 체크 기준표) 참조.

## 상태 관리

포팅 진행 상황은 워크플로우 repo가 아니라 **포팅 대상 게임 프로젝트의 `Docs/porting/{platform}-checklist.md`**에 기록·갱신된다 — 사람이 직접 확인·재검토할 수 있는 정본. 산출물 전체 목록은 `templates/README.md` 참조.

## 경로 규칙 (기여 시)

repo 안 파일끼리의 참조 경로 기준:
- 커맨드 상호참조 → `~/.claude/commands/...` (심볼릭 경유)
- 템플릿·스크립트·Editor → `$H5PW_ROOT/templates/...` (repo 직접)

새 문서·에이전트를 작성할 때 이 두 경로 형식만 사용한다 — 특정 사용자 홈 디렉토리를 가리키는 경로를 박지 않는다.

## 커밋 컨벤션 (기여 시)

커밋 메시지는 `[한글 프리픽스] 내용` 형식을 쓴다 (프리픽스 목록은 `templates/CLAUDE_Porting.md`의 "Commit Message Prefix" 표가 정본). 신규 플랫폼 포팅을 추가하면 그 표에 해당 플랫폼 프리픽스도 함께 추가한다.
