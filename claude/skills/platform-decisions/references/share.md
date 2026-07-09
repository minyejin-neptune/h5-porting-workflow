# 공유하기 — 문구·버튼 위치 확정

원본: `claude/agents/porting/platform-porter.md` 11단계. **두 분기(A/B) 모두 공유 문구 확정이 필요**하다 — h5-port STEP 3-A에서 더 이상 이 값을 사전 수집하지 않으므로(이슈 #48로 이관), 이 스킬이 유일한 확정 경로다.

**완료 신호**: `HLSDK.Instance.ShareLink(` 호출 이미 존재 → 스킵.

**탐색**: VOCAB `{SHARE_FILE}` → Read → grep fallback

```bash
grep -rn "NativeShare\|ShareLink\|OnClickShare\|UIButtonShare\|ShareButton" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

**공유 문구 확정 — AskUserQuestion**: "공유하기 문구를 화면별로 입력해주세요(예: 메인 화면, 결과 화면 등 — 화면이 여러 개면 각각)." 미확정 응답이면 플레이스홀더로 삽입 후 `// TODO: 공유 문구 기획 확인 필요` 주석 추가하고 `platform-checklist.md` `## 확인 필요`에 기록.

탐색 결과를 기반으로 분기:

## A. 기존 버튼 있음 — 기존 함수 내부에 전처리문 삽입

클릭 핸들러를 Read해서 함수 본문 확인. 확정된 공유 문구로 `HLSDK.Instance.ShareLink(문구)`를 `#if UNITY_WEBGL` 가드 안에 삽입.

> **코드 패턴**: `~/github/h5-porting-workflow/templates/porter-patterns/platform-patterns.md` → "11. 공유하기"

## B. 기존 버튼 없음

**버튼 위치·구현 방식 확정 — AskUserQuestion**: "공유 버튼이 없습니다 — 어느 화면·클래스에 신규로 추가할까요? (기존 UI 클래스에 삽입 / 전용 클래스 신규 중 선택)" (후보 클래스 목록 첨부)

확정되면 그 위치에 `HLSDK.Instance.ShareLink(문구)`를 `#if UNITY_WEBGL` 가드 안에 구현.

**검토 포인트**:
- 공유 버튼이 파생 클래스 구조면 기반 클래스 클릭 로직은 수정하지 않고 문구 인자만 화면별로 교체
- `#if UNITY_WEBGL` 가드 안에서만 호출되는지 확인
