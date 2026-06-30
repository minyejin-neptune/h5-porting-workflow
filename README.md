# h5-porting-workflow

Unity 모바일 게임을 **Toss / PureWeb WebGL(H5)** 로 포팅하는 Claude Code 워크플로우.
배포 방식: **git clone + 심볼릭 링크** (플러그인 아님). 편집은 repo에서, `git pull`로 전 프로젝트에 즉시 반영.

## 구조

```
claude/                       # ~/.claude 에 심볼릭될 내용
  agents/
    porter/    toss-porter, pureweb-porter
    design/    iap-analyzer, iaa-analyzer, save-point-analyzer
    unity-compile-checker, h5-game-porting-analyst, toss-sdk-expert
  commands/
    h5/        h5-port, porting-scan, porting-scan-verify
    project/   porting-init
templates/                    # ~/github/.templates 에 심볼릭될 내용
  CLAUDE_Porting.md, h5-porter-template.md, README.md
  scripts/h5-port-verify.py
  Editor/*.cs
install.sh                    # 위 둘을 심볼릭으로 연결
docs/                         # 내부 설계 문서
```

## 설치 (각자 1회)

```bash
git clone https://github.com/minyejin-neptune/h5-porting-workflow.git ~/github/h5-porting-workflow
cd ~/github/h5-porting-workflow
./install.sh
```

`install.sh` 가 하는 일:
- `claude/` 의 모든 파일 → `~/.claude/` 에 심볼릭 (agents·commands)
- `templates/` → `~/github/.templates` 에 심볼릭
- 기존 실제 파일/폴더가 있으면 `.bak` 으로 백업

설치 후 Claude Code에서 `/reload-plugins` 또는 재시작.

## 업데이트

```bash
cd ~/github/h5-porting-workflow && git pull
```
심볼릭이라 **별도 재설치 없이** 즉시 반영. 프로젝트의 Editor 스크립트도 `~/github/.templates` 경유라 자동 갱신.

## 사용

```bash
/h5:h5-port            # 전체 오케스트레이터 (STEP 0~4)
/h5:h5-port toss       # 토스 포팅 바로
/h5:porting-scan       # 사전 분석만
```

## 경로 규칙 (기여 시)

repo 안 파일끼리의 참조는 설치 후 경로 기준:
- 커맨드 상호참조 → `~/.claude/commands/...`
- 템플릿·스크립트·Editor → `~/github/.templates/...`

절대경로(`/Users/<이름>/...`)를 새로 박지 말 것. `~/.claude` · `~/github/.templates` 만 사용.

## ⚠️ 테스트 필요

- 커맨드 본문의 `~/.claude/commands/...` 참조를 Claude가 읽을 때 `~` 가 각 사용자 홈으로 풀리는지 (admin 외 팀원 머신에서 확인).

## 범위

- 포함: 코어 포팅(스캔/검증/포터/컴파일) + analyzer 3종(iap/iaa/save-point)
- 미포함: currency-analyzer, local-push-analyzer, biz-doc-writer (필요 시 추가)
