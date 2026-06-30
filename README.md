# h5-porting-workflow

Unity 모바일 게임을 **Toss / PureWeb WebGL(H5)** 로 포팅하는 Claude Code 워크플로우. 마켓플레이스 + 플러그인 1개로 구성.

## 구성

```
.claude-plugin/marketplace.json     # 마켓플레이스 정의 (name: neptune-h5-tools)
plugins/h5-porting/                 # 플러그인 (name: h5-porting)
  .claude-plugin/plugin.json
  agents/        toss-porter, pureweb-porter, unity-compile-checker,
                 h5-game-porting-analyst, toss-sdk-expert,
                 iap-analyzer, iaa-analyzer, save-point-analyzer
  commands/      h5-port, porting-scan, porting-scan-verify, porting-init
  templates/     CLAUDE_Porting.md, h5-porter-template.md, scripts/, Editor/
  docs/          REDESIGN.md, PORTING_WORKFLOW_STATUS.md
```

## 설치 (팀원)

```bash
/plugin marketplace add minyejin-neptune/h5-porting-workflow
/plugin install h5-porting@neptune-h5-tools
```

private repo이므로 git 인증(gh auth / SSH)이 돼 있어야 add 됩니다.

## 사용

```bash
/h5-porting:h5-port         # 전체 오케스트레이터 (STEP 0~4)
/h5-porting:h5-port toss    # 토스 포팅 바로
/h5-porting:porting-scan    # 사전 분석만
```

## 경로 규칙

플러그인 내부 파일 참조는 모두 `${CLAUDE_PLUGIN_ROOT}/...` 변수 사용 (절대경로 제거 완료).

## ⚠️ 첫 설치 후 테스트 필요 항목

공식 문서로 보장되지 않아 실제 환경에서 확인이 필요한 부분:

1. **커맨드 마크다운 본문 내 `${CLAUDE_PLUGIN_ROOT}` 확장** — `h5-port.md`가 `${CLAUDE_PLUGIN_ROOT}/commands/h5/porting-scan.md`를 "읽어서 실행"하는 상호참조. bash 블록(`cp`/`ln`/`python3`)에서는 동작 확인됨, **마크다운 본문 Read 경로 확장은 미검증** → 안 되면 커맨드 이름 호출(`/h5-porting:porting-scan`)로 전환 검토.
2. **`toss-sdk-expert` 외부 의존** — `/Users/admin/doc_develop/toss-sdk/` 로컬 문서 캐시를 읽음. 이 경로는 번들 불가(머신별) → 해당 에이전트 쓰려면 각자 문서 캐시 필요. 미보유 시 toss-sdk-expert는 동작 제한.

## 범위

- 포함: 코어 포팅(스캔/검증/포터/컴파일) + STEP 2-C가 호출하는 analyzer 3종(iap/iaa/save-point)
- 미포함: currency-analyzer, local-push-analyzer, biz-doc-writer (별도 영역 — 필요 시 추가)

## 인수인계 / 소유권 이전

개인 계정 → org 이전 절차는 플러그인 가이드 문서 §11 참조 (`claude-code-플러그인-가이드.md`). 요지: `marketplace.json`의 `name`(`neptune-h5-tools`) 유지하고 소스 repo만 교체.
