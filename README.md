# h5-porting-workflow

Unity 모바일 게임을 **Toss / PureWeb WebGL(H5)** 로 포팅하는 Claude Code 워크플로우

- 배포 방식: **git clone + 심볼릭 링크** (플러그인 아님)
- 편집은 repo에서, `git pull`로 전 프로젝트에 즉시 반영

## 파이프라인

```
STEP 0  프로젝트 초기 설정 (porting-init, HyperLane SDK 설치)
  →
STEP 1  EUC-KR → UTF-8 인코딩 변환
  →
STEP 2  프로젝트 분석 (porting-scan → porting-scan-verify)
  →
STEP 3  포터 실행
  pureweb-porter (SDK 초기화·로그인·저장·광고·IAP — HLSDK 공통 기반, 브라우저 테스트 가능)
    → platform-porter (HLSDK 서버 연동 — Toss/Kakao 공통)
      → toss-porter (Toss 전용 — 배너·프로모션 등)
  →
STEP 4  포팅 검증 (h5-port-verify.py)
```

전체 실행은 `/h5:h5-port` 하나로 오케스트레이션된다.

## 구조

```
claude/                       # ~/.claude 에 심볼릭될 내용
  agents/
    porting/    pureweb-porter, platform-porter, toss-porter, sdk-list-analyzer
    design/     iap-analyzer, iaa-analyzer, save-point-analyzer
  commands/
    h5/         h5-port, porting-scan, porting-scan-verify
    project/    porting-init
    analyze/    content-analyze
    common/     feature-breakdown, create-issue, resolve-issue, auto-resolve
templates/                    # 워크플로우가 repo 경로로 직접 참조 (심볼릭 없음)
  CLAUDE_Porting.md, h5-porter-template.md, README.md
  scripts/h5-port-verify.py, scripts/compile-check.sh
  Editor/*.cs, Runtime/*.cs
docs/
  기준-체크리스트.md           # 사람 수동 포팅 체크 표 — 워크플로우가 커버해야 하는 정답지
install.sh                    # claude/ 를 ~/.claude 로 심볼릭 연결
```

> **clone 위치 고정**: 워크플로우가 `~/github/h5-porting-workflow/templates/...` 를 직접 참조하므로
> repo는 반드시 **`~/github/h5-porting-workflow`** 에 clone해야 한다 (다른 경로면 템플릿 참조가 깨짐).

## 설치 (각자 1회)

```bash
git clone https://github.com/minyejin-neptune/h5-porting-workflow.git ~/github/h5-porting-workflow
cd ~/github/h5-porting-workflow
./install.sh
```

`install.sh` 가 하는 일:
- `claude/` 의 모든 파일 → `~/.claude/` 에 심볼릭 (agents·commands)
- 기존 실제 파일이 있으면 `.bak` 으로 백업

> `templates/` 는 심볼릭하지 않는다. 워크플로우가 `~/github/h5-porting-workflow/templates/` 를 직접 참조한다.

설치 후 Claude Code에서 `/reload-plugins` 또는 재시작.

## 업데이트

```bash
cd ~/github/h5-porting-workflow && git pull
```
`~/.claude` 는 심볼릭이라 **재설치 없이** 즉시 반영. 템플릿(`templates/`)도 repo 실파일이라 pull하면 바로 최신.
단, 이미 포팅한 프로젝트에 **복사된** Editor/Runtime 스크립트는 자동 갱신 안 됨(복사본) — 갱신하려면 porting-init 재실행 또는 수동 재복사.

## 사용

```bash
/h5:h5-port            # 전체 오케스트레이터 (STEP 0~4)
/h5:h5-port toss        # 토스 포팅 바로 (pureweb-porter → platform-porter → toss-porter 순서로 자동 진행)
/h5:h5-port pureweb     # 퓨어웹만
/h5:porting-scan        # 사전 분석만
```

개별 포터를 직접 호출할 수도 있다(`Agent 도구, subagent_type: "pureweb-porter"` 등) — 이 경우 각 포터가 선행 포터 완료 여부를 진입점에서 스스로 확인하고, 안 됐으면 대신 실행하지 않고 안내만 한 뒤 반환한다.

## 경로 규칙 (기여 시)

repo 안 파일끼리의 참조 경로 기준:
- 커맨드 상호참조 → `~/.claude/commands/...` (심볼릭 경유)
- 템플릿·스크립트·Editor·Runtime → `~/github/h5-porting-workflow/templates/...` (repo 직접)

새 문서·에이전트를 작성할 때 이 두 경로 형식만 사용한다 — 특정 사용자 홈 디렉토리를 가리키는 경로를 박지 않는다.

## 범위

- 포함: 코어 포팅(스캔/검증/포터/컴파일) + analyzer 3종(iap/iaa/save-point) + content-analyze
- 미포함: currency-analyzer, local-push-analyzer, biz-doc-writer (필요 시 추가)
