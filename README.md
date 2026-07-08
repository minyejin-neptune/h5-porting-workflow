# h5-porting-workflow

Unity 모바일 게임을 **Toss / PureWeb WebGL(H5)** 로 포팅하는 Claude Code 워크플로우.
배포 방식: **git clone + 심볼릭 링크** (플러그인 아님). 편집은 repo에서, `git pull`로 전 프로젝트에 즉시 반영.

## 구조

```
claude/                       # ~/.claude 에 심볼릭될 내용
  agents/
    porter/    toss-porter, pureweb-porter
    design/    iap-analyzer, iaa-analyzer, save-point-analyzer
    unity-compile-checker, toss-sdk-expert
  commands/
    h5/        h5-port, porting-scan, porting-scan-verify
    project/   porting-init
    analyze/   content-analyze
templates/                    # 워크플로우가 repo 경로로 직접 참조 (심볼릭 없음)
  CLAUDE_Porting.md, h5-porter-template.md, README.md
  scripts/h5-port-verify.py
  Editor/*.cs, Runtime/*.cs
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
- (구버전 `~/github/.templates` 심볼릭이 있으면 제거)

> `templates/` 는 심볼릭하지 않는다. 워크플로우가 `~/github/h5-porting-workflow/templates/` 를 직접 참조한다.

설치 후 Claude Code에서 `/reload-plugins` 또는 재시작.

## 업데이트

```bash
cd ~/github/h5-porting-workflow && git pull
```
`~/.claude` 는 심볼릭이라 **재설치 없이** 즉시 반영. 템플릿(`templates/`)도 repo 실파일이라 pull하면 바로 최신.
단, 이미 포팅한 프로젝트에 **복사된** Editor 스크립트는 자동 갱신 안 됨(복사본) — 갱신하려면 porting-init 재실행 또는 수동 재복사.

## 사용

```bash
/h5:h5-port            # 전체 오케스트레이터 (STEP 0~4)
/h5:h5-port toss       # 토스 포팅 바로
/h5:porting-scan       # 사전 분석만
```

## 경로 규칙 (기여 시)

repo 안 파일끼리의 참조 경로 기준:
- 커맨드 상호참조 → `~/.claude/commands/...` (심볼릭 경유)
- 템플릿·스크립트·Editor·Runtime → `~/github/h5-porting-workflow/templates/...` (repo 직접)

절대경로(`/Users/<이름>/...`)를 새로 박지 말 것. `~/.claude` · `~/github/h5-porting-workflow/templates` 만 사용.

## ⚠️ 테스트 필요

- 커맨드 본문의 `~/.claude/commands/...` 참조를 Claude가 읽을 때 `~` 가 각 사용자 홈으로 풀리는지 (admin 외 팀원 머신에서 확인).

## 범위

- 포함: 코어 포팅(스캔/검증/포터/컴파일) + analyzer 3종(iap/iaa/save-point) + content-analyze
- 미포함: currency-analyzer, local-push-analyzer, biz-doc-writer (필요 시 추가)
