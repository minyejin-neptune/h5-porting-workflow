# 햅틱 — 삽입 위치·Tier 확정

원본: `claude/agents/porting/platform-porter.md` 8단계(platform-porter는 이 절차를 실행하지 않고 이 스킬로 이관한다).

**완료 신호**: 대상 위치에 `HapticController.Generate(` 호출 이미 존재 → 스킵.

**탐색**: VOCAB `{HAPTIC_FILE}` → Read → grep fallback

```bash
grep -rn "Vibrate\|Haptic\|haptic\|vibrate" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
grep -rn "GenerateHapticFeedback\|HapticController" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

## HapticController 유틸 준비

iOS·Android는 같은 의도(약함·중간 등)라도 `tick`·`basic` 타입의 체감 강도가 반대로 느껴진다 — 플랫폼별로 다른 타입을 배정해야 한다. 이 매핑을 `HapticTier` enum으로 추상화한 공용 템플릿을 쓴다.

- 위 grep에서 이미 `HapticController`(또는 유사 Tier 기반 유틸)가 있으면 → 재사용, 아래 복사 생략.
- 없으면 공용 템플릿을 프로젝트로 **복사**한다.

> ⚠️ 심볼릭 링크 금지 — 원격/CI 빌더엔 `$H5PW_ROOT/templates`가 없어 dangling 링크로 깨진다. 반드시 복사해 프로젝트 git에 실파일로 커밋되게 한다.

- 템플릿 위치: `$H5PW_ROOT/templates/Runtime/HapticController.cs`
- `.cs`를 복사한다. `.meta`는 Unity가 프로젝트 로컬에 생성한다:
  ```bash
  mkdir -p {SCRIPTS_PATH}/Utility
  cp $H5PW_ROOT/templates/Runtime/HapticController.cs \
     {SCRIPTS_PATH}/Utility/HapticController.cs
  ```
- 사용 가능한 Tier(정의는 템플릿이 유일한 소스): `Weak`·`WeakStrong`·`Medium`·`MediumStrong`·`Soft`·`Tap`·`Success`·`Confetti`. 필요한 효과가 없으면 `HLSDK.Instance.GenerateHapticFeedback("{타입}")`을 직접 호출한다(예외적인 경우로 한정).
- 복사 방식이라 프로젝트마다 사본이 생긴다. 템플릿을 고치면 각 프로젝트에서 재복사해야 반영된다.

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
