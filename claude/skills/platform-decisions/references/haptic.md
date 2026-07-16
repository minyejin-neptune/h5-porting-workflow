# 햅틱 — 삽입 위치·Tier 확정

원본: `claude/agents/porting/platform-porter.md` 8단계(platform-porter는 이 절차를 실행하지 않고 이 스킬로 이관한다).

**완료 신호**: 대상 위치에 `HapticController.Generate(` 호출 이미 존재 → 스킵.

**탐색**: VOCAB `{HAPTIC_FILE}` → Read → grep fallback

```bash
grep -rn "Vibrate\|Haptic\|haptic\|vibrate" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
grep -rn "GenerateHapticFeedback\|HapticController" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

## HapticController 유틸

iOS·Android는 같은 의도(약함·중간 등)라도 `tick`·`basic` 타입의 체감 강도가 반대로 느껴진다 — 플랫폼별로 다른 타입을 배정해야 한다. 이 매핑은 `HLSDK.HapticController`(HLSDK 패키지에 내장)의 `HapticTier` enum으로 이미 추상화되어 있다 — 프로젝트로 별도 복사할 필요 없음.

- 사용 가능한 Tier(정의는 HLSDK 패키지가 유일한 소스): `Weak`·`WeakStrong`·`Medium`·`MediumStrong`·`Soft`·`Tap`·`Success`·`Confetti`. 필요한 효과가 없으면 `HLSDK.Instance.GenerateHapticFeedback("{타입}")`을 직접 호출한다(예외적인 경우로 한정).
- 위 grep에서 프로젝트 로컬에 별도의 Tier 기반 유틸(구버전 복사본 등)이 있으면 정리 대상인지 확인 — HLSDK 내장 버전으로 통일한다.

## 탐색 결과에 따라 분기

**기존 진동 호출 있는 경우** → 기존 호출의 세기 표현(주석·변수명·컨텍스트)을 참고해 적절한 Tier를 판단하고 아래 코드 패턴으로 교체.

**기존 진동 호출 없는 경우**:

1. content-analyze 스킬로 인게임 이벤트 후보를 조사한다(코드 삽입 없이 조사만):
   ```
   /analyze:content-analyze 인게임 로직 --docs 역기획서
   ```
2. 조사 결과를 후보로 정리한다.

   | 위치(파일:라인) | 이벤트 | 제안 Tier | 쿨다운 |
   |---|---|---|---|
   | ... | ... | ... | 없음 / N초 |

3. **AskUserQuestion으로 확정**: "위 후보 중 어느 위치·Tier로 햅틱을 삽입할까요?" (후보 표 첨부, "직접 지정" 선택지도 포함)
4. 확정 답변에 따라 코드 삽입. 미확정 응답(사용자가 나중에 결정하겠다고 하면) → `platform-checklist.md` `## 확인 필요`에 후보 표 기록하고 이 단계는 스킵(HapticController 유틸 복사까지만 완료 처리).

> **코드 패턴**: `$H5PW_ROOT/templates/porter-patterns/platform-patterns.md` → "8. 햅틱"
