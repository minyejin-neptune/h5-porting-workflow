# 불필요한 UI 삭제 — 대상 확정

원본: `claude/agents/porting/platform-porter.md` 14단계. **기존 방치 버그 항목** — h5-port STEP 3-A 사전 질문 표에 이 항목이 없어서 재질문 경로 자체가 없이 체크리스트에만 쌓이던 항목이다. 이 스킬이 최초로 실제 질문 경로를 갖는다.

WebGL에서 의미 없는 네이티브 전용 UI를 비활성화한다.

**탐색**: VOCAB `{REMOVE_UI_LIST}` → scan이 찾은 **후보** 목록 확인(scan은 확정하지 않는다).

`{REMOVE_UI_LIST}` 가 "없음"이면 이 단계는 대상이 없으니 종료.

**삭제 대상 확정 — AskUserQuestion**: "아래 후보 UI 중 WebGL에서 비활성화할 항목을 선택해주세요(일부는 법적/정책 요구사항일 수 있으니 신중히 — 예: 리뷰 유도, 문의하기 링크 등)." (VOCAB `{REMOVE_UI_LIST}` 파일:라인 후보 목록 전부 제시, 항목별로 포함/제외 선택)

확정된 항목만 `#if !UNITY_WEBGL` 가드로 비활성화. 미확정이면 `platform-checklist.md` `## 확인 필요`에 후보 목록 기록하고 스킵.

> **코드 패턴**: `$H5PW_ROOT/templates/porter-patterns/platform-patterns.md` → "14. 불필요한 UI 삭제"
