---
description: TRIGGER — 포팅 코드 수정 후 `❌ 미처리`/`⚠️ 확인 필요` 검증이 필요할 때, 또는 h5-port-verify.py 실행이 필요한 상황(포터 자체검증·STEP4 최종검증)에서 사용. 결과 해석(❌/⚠️/✅)과 verify-exceptions.json 처리까지 전담한다.
effort: max
---

# porting-verify

포팅 수행(포터)과 검증을 분리하기 위한 스킬. `h5-port-verify.py`를 실행하고, `❌ 미처리`/`⚠️ 확인 필요` 결과를 사람 판단으로 연결하는 절차까지 담당한다.

> **추론 금지**: 검증 결과·코드 근거는 실제 출력·Read로 확인한 것만 기재한다.

## 호출 방법

`$ARGUMENTS` 형식: `{platform} {narrow|full} {인자...}`

- **narrow 모드** — 포터가 자기 자신이 방금 작업한 특정 메서드만 검사할 때. 형식: `{platform} narrow {scripts-path} {checklist-file} {method1} [method2] ...`
  예: `WEBGL_PUREWEB narrow Assets/Scripts pureweb-checklist.md AD_REWARDED_METHOD_실제값 IAP_METHOD_실제값 SAVE_METHOD_실제값`
- **full 모드** — VOCAB 전체 기준 포괄 검증(h5-port.md STEP 4, 또는 포터의 단독 실행 완료 시 최종 확인). 형식: `{platform} full {scripts-path} {vocab-path} {checklist-file}`
  예: `WEBGL_TOSS full Assets/Scripts Docs/porting/PORTING_VOCAB.md toss-checklist.md`

호출자는 `{method}` 값을 VOCAB 플레이스홀더 이름이 아니라 **실제 코드에 존재하는 메서드/패턴 이름**(VOCAB에서 이미 읽은 값, 또는 HLSDK 고정 API 이름)으로 넘긴다 — 이 스킬은 플레이스홀더를 해석하지 않는다.

## 1단계 — 스크립트 실행

```bash
# narrow 모드
python3 $H5PW_ROOT/templates/scripts/h5-port-verify.py \
  --platform {platform} \
  --scripts {scripts-path} \
  --method {method1} --method {method2} ...

# full 모드
python3 $H5PW_ROOT/templates/scripts/h5-port-verify.py \
  --platform {platform} \
  --vocab {vocab-path} \
  --scripts {scripts-path}
```

결과는 `❌ 미처리`(가드 없이 메서드 호출 — 실제 이슈) / `⚠️ 확인 필요`(`#elif UNITY_WEBGL` 블록 안 호출 — 사람 판단 필요) / `✅ 이상 없음` 세 가지다.

| 결과 | 대응 |
|---|---|
| `✅ 이상 없음` | 완료 — 호출자에게 반환 |
| `❌ 미처리` | 아래 "❌ 항목 기록" 수행 후 호출자에게 반환 — 호출자가 코드 수정 후 이 스킬 재호출 |
| `⚠️ 확인 필요` | 2단계로 진행 |

### ❌ 항목 기록

`❌ 미처리` 결과가 있으면 코드 수정 전에 먼저 기록한다. 기록 대상은 호출 시 받은 `{checklist-file}`에 따라 다르다 — `## 이슈` 섹션이 없는 파일(`platform-checklist.md`)은 자체 기록 대상이 아니므로 리다이렉트한다(신규 공통 이슈 발견 시 `platform-porter.md`가 이미 쓰는 컨벤션과 동일):

| `{checklist-file}` | 기록 대상 | 태그 |
|---|---|---|
| `pureweb-checklist.md` | 자기 자신의 `## 이슈` | `[검증]` |
| `toss-checklist.md` | 자기 자신의 `## 이슈` | `[검증]` |
| `platform-checklist.md` | 같은 `Docs/porting/` 안의 `pureweb-checklist.md` `## 이슈` | `[검증:platform]` |

기록 형식: `- [ ] {파일}:{라인} — {태그} {패턴 요약}`

## 2단계 — ❌/⚠️ 항목 처리 (패턴 분석 → 확정 → exceptions 기록)

**사용자가 JSON을 직접 작성하지 않는다.** 이 스킬이 아래 순서로 처리한다.

### 2-1. 패턴 분석

❌/⚠️ 항목을 Read로 실제 코드 확인 후 패턴별로 묶는다(건별이 아니라 패턴 단위):

| 패턴 | 예시 | 판단 근거 |
|---|---|---|
| 위임 호출 | `IAPManager.Instance.Purchase(...)` | 호출 대상 정의에 이미 가드 있음 |
| `#elif UNITY_WEBGL` 분기 | `DataController.cs:167` | 이미 플랫폼 전용 분기 안에 있을 가능성 |
| 진짜 미처리 | 가드 없이 직접 SDK 호출 | 수정 필요 |

### 2-2. 확정 — AskUserQuestion 우선, 안 되면 결정 필요 라우팅

패턴 단위로 확정한다. 잘못 "안전" 처리하면 실제 버그가 검증을 통과해 숨겨지므로, 이 스킬은 임의로 safe 판정하지 않는다.

- **메인 세션(h5-port.md)에서 호출된 경우**: AskUserQuestion으로 그 자리에서 바로 확인한다 — "{패턴 요약} {건수}건이 {근거 파일:라인} 패턴입니다. safe 처리할까요?"
- **서브에이전트(포터) 컨텍스트에서 호출된 경우**: 서브에이전트는 실행 중 사용자에게 질문할 수 없다(AskUserQuestion 불가) — `{checklist-file}` `## 확인 필요`에 `- [ ] verify ❌/⚠️ 패턴별 safe 판정 — {패턴 요약과 건수, 근거 파일:라인}` 형식으로 기록하고, 판정 전까지 해당 항목은 미처리 상태로 둔다. 확정 답변은 h5-port 후속 모드(재실행 시 미확정 재질문)가 수집·반영한다.

호출 컨텍스트 판단: AskUserQuestion 도구를 실제로 시도해본다 — 사용 가능하면 메인 세션, 도구 자체가 없거나 호출이 차단되면 서브에이전트로 간주하고 위 라우팅 절차로 넘어간다.

### 2-3. verify-exceptions.json 기록

확정("safe"/"unsafe")된 패턴을 `Docs/porting/verify-exceptions.json`에 기록한다:

```json
[
  {
    "file": "Assets/Scripts/Data/DataController.cs",
    "directive_line": 167,
    "directive": "#elif UNITY_WEBGL",
    "decision": "safe",
    "note": "PlayerPrefs 로드 — 사용자 확인"
  }
]
```

- `decision: "safe"` → 다음 실행 시 자동 필터링
- `decision: "unsafe"` → 실제 이슈, 호출자에게 수정 필요로 반환

### 2-4. 재검증

기록 후 1단계 스크립트를 동일 인자로 재실행해, 해당 항목이 `✅ 로그 필터링`으로 바뀌는지 확인한다. 확정하지 못한(미확정) 패턴은 그대로 `⚠️ 확인 필요`로 남고, 호출자에게 "미확정 N건, `{checklist-file}` 참조"로 보고한다.

## 최종 반환

호출자(포터 또는 h5-port.md)에게 아래 형식으로 요약해 반환한다:

```
검증 결과: ✅ 이상 없음 {N}건 / ❌ 미처리 {N}건 / ⚠️ 확인 필요(미확정) {N}건
{❌ 있으면 "대표 최대 3건: {파일:라인 최대 3개} — 전체는 {기록 대상 파일} `## 이슈` 참조"}
{⚠️ 미확정 있으면 "{checklist-file} `## 확인 필요` 참조"}
```
