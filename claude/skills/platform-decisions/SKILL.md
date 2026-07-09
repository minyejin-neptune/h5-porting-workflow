---
description: platform-porter의 스텝 중 사람 판단이 필요한 6개(햅틱·랭킹버튼·공유하기·UID/version·불필요UI삭제·로컬라이제이션)를 사용자가 직접 호출해 처리하는 스킬. 메인 세션에서 도니 AskUserQuestion을 바로 쓸 수 있다.
effort: high
---

# platform-decisions

`$ARGUMENTS`로 키워드 하나를 받아 해당 판단 항목만 처리한다. 인자가 없으면 `platform-checklist.md`를 스캔해 대기 중인 항목을 보여준다.

> **공용 규칙**: `templates/porter-rule.md`를 Read해서 따른다(탐색 기본 원칙·문서 오류 교정 기록·에디터 섀도잉 금지·전처리문 규칙 등). 이 스킬은 platform-porter와 동일한 `platform-checklist.md`를 정본으로 쓴다. `{PLATFORM_SYMBOL}`은 `.porting-context`로 현재 선택된 플랫폼을 읽어 사용(예: 없으면 `UNITY_WEBGL` 단독으로 충분 — porter-rule.md 참조).

> **추론 금지**: 코드·에셋에서 직접 확인한 사실만 기재한다.

## 키워드 라우팅

| 키워드 | 참고 파일 |
|---|---|
| 햅틱 | `references/haptic.md` |
| 랭킹버튼 | `references/ranking.md` |
| 공유 | `references/share.md` |
| UID | `references/uid-version.md` |
| UI삭제 | `references/remove-ui.md` |
| 로컬라이제이션 | `references/localization.md` |

`$ARGUMENTS`가 위 키워드 중 하나면 해당 참고 파일을 Read해서 그 절차만 실행한다. 다른 스텝은 건드리지 않는다.

## 무인자 진입 — 대기 항목 스캔

`$ARGUMENTS`가 비어 있으면:

1. `Docs/porting/platform-checklist.md` `## 확인 필요`를 Read해서 위 6개 키워드와 관련된 미해결(`- [ ]`) 항목을 찾는다.
2. `## 단계 진행`에서 8·10-1·11·13·14·15 스텝의 완료 상태도 함께 확인한다.
3. 대기 중인 항목을 목록으로 보여주고, 어떤 걸 먼저 처리할지 AskUserQuestion으로 확인한다. 목록이 비어 있으면 "대기 중인 판단 항목 없음"을 출력하고 종료한다.
4. 선택된 키워드로 위 라우팅 표를 따라 진행한다.

## 처리 후 공통 절차

각 참고 파일의 절차를 마친 뒤:

1. `platform-checklist.md` `## 단계 진행`의 해당 스텝을 갱신(`- [x] {단계} — ✅ commit {해시7자리}`).
2. `## 확인 필요`에 있던 관련 항목을 해소(체크박스 제거 또는 `- [x]`로 갱신).
3. `.cs` 파일을 수정했으면 `git commit -m "[웹지엘] {단계명}"`.
4. 스텝ID:이슈번호 매핑이 있으면(포팅 이슈 #47 체계) 해당 이슈에도 완료를 반영한다 — 없으면 생략.

## 완료 후 출력

```
✅ platform-decisions 완료 — {처리한 키워드}

{처리 내용 요약: 확정값·삽입 위치·커밋 해시}

다음: /platform-decisions (인자 없이) 로 남은 대기 항목 확인
```
