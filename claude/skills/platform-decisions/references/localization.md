# 로컬라이제이션 — 자동 확인

원본: `claude/agents/porting/platform-porter.md` 15단계. **판단 지점이 아니다** — 두 분기 다 확인 없이 진행되는 순수 자동 로직이라, 이 스킬에서도 새로운 질문을 추가하지 않고 원본 로직을 그대로 옮긴 것뿐이다. 로컬라이제이션 자체가 필요한지 여부는 사용자가 상황을 보고 이 스킬을 호출할지 말지로 직접 결정한다.

**완료 신호**: `WebUtil.Instance.GetSystemLang()` 사용 이미 존재 → 스킵.

**탐색**: VOCAB `{LOCALIZATION_FILE}` → Read → grep fallback

```bash
grep -rn "Localization\|LocalizationManager\|I2Loc\|GetSystemLang\|systemLanguage\|WebUtil.*Lang" {SCRIPTS_PATH} --include="*.cs" | grep -v HyperLane
```

탐색 결과로 분기한다(어느 쪽이든 확인 없이 진행):

- **이미 구현됨** → WebGL에서 `WebUtil.Instance.GetSystemLang()` 사용 여부만 확인.
- **미구현** → `platform-checklist.md` `## 확인 필요`에 "로컬라이제이션 미구현 — 범위 결정 후 별도 작업" 기록.

> 코드 패턴 없음 — `templates/porter-patterns/platform-patterns.md`에 이 항목 섹션 없음(확인됨, grep 0건). 위 두 분기 외 추가 구현 지시가 필요하면 그때 사용자에게 직접 물어본다.
