---
description: 포팅 스캔 검증 — NATIVE_BASELINE·pureweb-checklist·VOCAB가 실제 코드와 일치하는지 7종 병렬 검증
---

# 포팅 스캔 검증

`Docs/porting/NATIVE_BASELINE.md`·`pureweb-checklist.md`·`PORTING_VOCAB.md`를 읽어 porting-scan 결과가 실제 코드와 일치하는지 검증한다.

> **verify = NATIVE_BASELINE 동결 전 마지막 교정 단계.** 여기서 불변 사실(외부 SDK 목록·프로젝트 정보·게임 구조·빌드 씬)의 오류를 바로잡고, 이후 baseline은 동결한다.

추론 금지. 코드에서 직접 확인한 사실만 기재. 불일치 발견 시:
- 불변 사실(외부 SDK 목록·프로젝트 정보·게임 구조·빌드 씬) → `NATIVE_BASELINE.md` 직접 수정
- 이슈(컴파일/런타임/공백)의 발견·처리 상태 → `pureweb-checklist.md` `## 이슈` 체크박스 (`- [ ]`/`- [x]`)

---

## 사전 확인

```bash
# NATIVE_BASELINE.md 존재 여부
ls Docs/porting/NATIVE_BASELINE.md 2>/dev/null && echo "EXISTS" || echo "NONE"

# SCRIPTS_PATH (NATIVE_BASELINE.md 상단에서 읽기)
head -5 Docs/porting/NATIVE_BASELINE.md
```

NATIVE_BASELINE.md가 없으면 "먼저 /porting-scan을 실행하세요"라고 안내하고 종료.

---

## 파이프라인

```
[병렬] VERIFY-A | VERIFY-D | VERIFY-BUILD-SCRIPT | VERIFY-VOCAB | VERIFY-STORAGE | VERIFY-RUNTIME | VERIFY-VOID
      ↓
[순차] VERIFY-COMPILE 안내
      ↓
[순차] 결과 요약 + 불일치 항목 수정 (불변→NATIVE_BASELINE / 이슈→pureweb-checklist)
```

---

### VERIFY-A — A 처리 누락 파일 검증

NATIVE_BASELINE.md의 외부 SDK 목록에서 처리방법이 **A**인 SDK를 추출한다.
각 SDK의 네임스페이스로 `UNITY_WEBGL` 가드 없는 파일을 재탐색한다.

```bash
# A 대상 SDK 네임스페이스별로 — UNITY_WEBGL 가드 없는 using 파일
grep -rln "using {SDK네임스페이스}" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | xargs -I{} sh -c 'grep -l "UNITY_WEBGL" {} 2>/dev/null || echo "A_MISSING: {}"'
```

- `A_MISSING:` 파일이 있으면 → scan 누락. pureweb-checklist.md `## 이슈`에 `- [ ] {파일} — [컴파일] A_MISSING: UNITY_WEBGL 가드 없음 — A` 추가
- 없으면 → A 처리 완전

**CALLER_MISSING · INTERNAL_UNGUARDED 재탐지**

pureweb-checklist.md `## 이슈`에 `CALLER_MISSING` 또는 `INTERNAL_UNGUARDED` 항목이 있으면 scan-callers로 재탐지한다.

```bash
python3 Docs/porting/h5-port-verify.py \
  --platform {PLATFORM_SYMBOL} \
  --mode scan-callers \
  --wrapper {A처리파일1} \
  --wrapper {A처리파일2} \
  --scripts {SCRIPTS_PATH}
# EXTRA_PATHS가 있으면 --scripts 반복 추가
```

| 결과 | 처리 |
|---|---|
| 동일 파일:라인이 여전히 출력됨 | 해당 `## 이슈` 항목 `- [ ]` 유지 |
| 출력에서 사라짐 | 해당 `## 이슈` 항목 `- [x]`로 체크 |
| 신규 `CALLER_MISSING` 발견 | pureweb-checklist `## 이슈`에 `- [ ]` 추가 |

`CALLER_MISSING`·`INTERNAL_UNGUARDED` 항목이 없으면 → porting-scan 래퍼 역추적이 실행되지 않은 것. 이 자리에서 직접 실행한다.

---

### VERIFY-D — D 처리 meta 파일 전수 검사

NATIVE_BASELINE.md에서 처리방법이 **D**인 SDK 폴더를 추출한다.
해당 폴더의 `.dll`, `.aar`, `.framework` meta 파일에서 `WebGL: enabled: 1` 잔존 여부를 확인한다.

```bash
# D 대상 SDK 폴더별로
find {SDK_FOLDER} \( -name "*.dll.meta" -o -name "*.aar.meta" -o -name "*.framework.meta" \) 2>/dev/null \
  | xargs grep -l "WebGL: enabled: 1" 2>/dev/null
```

- 결과가 있으면 → WebGL 비활성화 미처리. pureweb-checklist.md `## 이슈`에 `- [ ] {SDK 폴더}/{meta} — [SDK] WebGL 비활성화 미처리 — .meta WebGL: enabled: 0` 추가
- 없으면 → D 처리 완전

---

### VERIFY-BUILD-SCRIPT — 자체 빌드 스크립트 재탐색

scan에서 사용한 `BuildPlayer|BuildPipeline` 패턴에 빌드 훅 패턴을 추가해 재탐색한다.

```bash
# 직접 빌드 호출 + 빌드 훅 인터페이스
grep -rln "BuildPlayer\|BuildPipeline\|IPreprocessBuildWithReport\|IPostprocessBuildWithReport\|OnPreprocessBuild\|OnPostprocessBuild" \
  Assets --include="*.cs" 2>/dev/null | grep -v HyperLane
```

scan 결과와 비교:
- 새로 발견된 파일 → Read해서 내용 분석 후 NATIVE_BASELINE.md 프로젝트 정보 테이블 업데이트
- 동일하면 → 이상 없음

---

### VERIFY-VOCAB — PORTING_VOCAB.md 정확성 검증

PORTING_VOCAB.md의 각 행에서 파일:라인을 읽어 실제 코드의 해당 라인과 1:1 대조한다.
재스캔이 아니라 **기록된 주장의 정확성**을 검증한다.

**1단계 — 파일:라인 spot-check**

각 행의 파일:라인을 추출해 해당 라인을 읽고, 기록된 메서드/클래스명이 실제로 있는지 확인한다.

```bash
# 각 행에 대해 실행 (파일:라인이 "...", "없음", "확인 필요"인 행은 스킵)
sed -n '{라인}p' {파일경로} 2>/dev/null
```

판정:
- 기록된 메서드/클래스명이 해당 라인에 있으면 → ✅ 정확
- 라인 내용이 다르거나 파일이 없으면 → ❌ 불일치. PORTING_VOCAB.md 해당 행을 "확인 필요"로 수정

**2단계 — 공통 플레이스홀더 미채움 확인**

플레이스홀더 목록을 여기서 따로 유지하지 않는다 — 메인 표에서 "미채움(`...`)이면서 플레이스홀더(`{...}`)가 배정된 행"을 직접 찾는다. 목록이 아니라 실제 생성된 파일을 기계적으로 스캔하므로, porting-scan.md의 VOCAB 템플릿이 바뀌어도(행 추가·제거) 이 검사는 그대로 유효하다.

```bash
sed -n '/^| 시스템 | 메서드\/클래스명/,/^## Toss 전용/p' Docs/porting/PORTING_VOCAB.md | grep -E '\.\.\..*\{[A-Z_]+\}'
```

결과가 있으면 그 행 전체를 보여준다(행 자체에 시스템명·플레이스홀더가 이미 있다):
> "아래 VOCAB 행이 비어있어 포터에서 플레이스홀더를 채울 수 없습니다:"
> {매칭된 행 그대로 나열}

**3단계 — Toss 전용 플레이스홀더 미채움 확인**

`## Toss 전용` 섹션에서 플레이스홀더 열이 `...`인 행을 추출한다.

```bash
grep -A20 "## Toss 전용" Docs/porting/PORTING_VOCAB.md | grep "\.\.\."
```

`없음`은 정상. `...`만 미채움으로 처리한다.

미채움 행이 있으면:
> "Toss 전용 VOCAB 행이 비어있습니다. porting-scan 4-I를 재실행하거나 직접 입력해주세요:"
> - `{BANNER_FILE}` ← 배너 광고 행 미채움
> *(해당 항목만 나열)*

**4단계 — 저장 인코딩 행 확인**

`저장 인코딩` 행이 `...` 또는 `확인 필요`이면 포터가 Base64 래핑 필요 여부를 판단할 수 없다.

미채움이면:
> "저장 인코딩 행이 비어있습니다. porting-scan 4-E 4단계를 재실행하거나 직접 입력해주세요."

**5단계 — 빌드 씬 파일 누락 확인**

NATIVE_BASELINE.md의 빌드 씬 행에 `❌ 파일 없음` 항목이 있으면 사용자에게 보고한다.

```bash
grep "빌드 씬" Docs/porting/NATIVE_BASELINE.md
```

`❌`이 포함되어 있으면:
> "Build Settings에 등록됐지만 실제 파일이 없는 씬이 있습니다. 씬 파일을 추가하거나 Build Settings에서 제거하세요."

---

### VERIFY-STORAGE — File 저장 WebGL 가드 누락 확인

`File.Write` 계열 저장이 `#if !UNITY_WEBGL` 가드 없이 WebGL에서 실행되는 경로가 있는지 확인한다.

```bash
grep -rn "File\.WriteAllBytes\|File\.WriteAllText\|StreamWriter\|BinaryWriter" \
  Assets/Scripts --include="*.cs" 2>/dev/null \
  | grep -v "UNITY_WEBGL\|HyperLane\|//"
```

- 결과 없음 → 이상 없음
- 결과 있음 → 해당 파일을 Read해서 실제로 WebGL에서 실행 가능한 경로인지 확인 후 pureweb-checklist.md `## 이슈`에 `- [ ]` 항목으로 추가

**보강 — File.Write 래퍼 케이스**

위 grep이 0건이어도 `using System.IO`가 있는 파일은 래퍼를 통해 파일 IO를 호출할 수 있다.

```bash
grep -rln "using System\.IO" {SCRIPTS_PATH} --include="*.cs" 2>/dev/null \
  | grep -v HyperLane | head -5
```

히트 파일이 있으면 상위 5개를 Read해 File.Write/Read 계열 실제 호출(파일:라인)이 있는지 확인한다.
- 직접 호출 확인 → pureweb-checklist.md `## 이슈`에 `- [ ]` 항목으로 추가
- 호출 없음(import만) → 이상 없음

> 저장 키 충돌 위험(PlayerPrefs 키 패턴) 판단은 scan 결과를 보고 사용자가 직접 판단한다.

---

### VERIFY-RUNTIME — 런타임 이슈 기록 정확성 검증

pureweb-checklist.md `## 이슈`의 `[런타임]` 항목에서 파일:라인을 추출해 실제 코드와 1:1 대조한다.
재스캔이 아니라 **기록된 주장이 실제 코드와 일치하는지** 검증한다.

`## 이슈`의 `[런타임]` 항목에서 파일:라인이 기록된 것을 읽어 해당 라인을 확인한다:

```bash
# 각 런타임 이슈 행에 대해 실행
sed -n '{라인}p' {파일경로} 2>/dev/null
```

판정:

| 결과 | 의미 | 처리 |
|---|---|---|
| 기록된 패턴(UnityWebRequest 등)이 있고 UNITY_WEBGL 가드 없음 | ✅ 기록 정확 | 그대로 유지 |
| 라인 내용이 전혀 다름 | ❌ 라인 참조 오류 | pureweb-checklist `## 이슈` 해당 항목의 파일:라인 수정 |
| 이미 `#if !UNITY_WEBGL` 가드가 붙어있음 | ℹ️ 이미 처리됨 | 해당 `## 이슈` 항목을 `- [x]`로 체크 |

`[런타임]` 이슈 항목이 비어있으면:
- SDK가 5개 이상 있는데 런타임 이슈 0건 → 스캔 누락 가능성. 사용자에게 보고한다.
- SDK가 없거나 적으면 → 정상으로 간주

---

### VERIFY-VOID — WebGL 공백 처리 검증

pureweb-checklist.md `## 이슈`의 `[공백]` 항목 각각의 처리 여부를 재스캔으로 확인한다.

```bash
python3 Docs/porting/h5-port-verify.py \
  --platform {PLATFORM_SYMBOL} \
  --scripts {SCRIPTS_PATH} \
  --mode scan-void
# EXTRA_PATHS가 있으면 --scripts 반복 추가
```

재스캔 결과와 테이블을 비교한다:

| 결과 | 의미 | 처리 |
|---|---|---|
| 동일 파일:라인이 여전히 출력됨 | 미처리 | 해당 `## 이슈` 항목 `- [ ]` 유지 |
| 출력에서 사라짐 | WebGL arm 추가 완료 | 해당 `## 이슈` 항목 `- [x]`로 체크 |
| 신규 `CONTROL_FLOW`·`STATE_UNDEF` 발견 | scan 이후 신규 발생 또는 scan 누락 | pureweb-checklist `## 이슈`에 `- [ ]` 추가 |

`## WebGL 공백 이슈` 테이블이 없거나 비어있으면 → porting-scan STEP 6이 실행되지 않은 것. 이 자리에서 직접 실행한다.

---

### VERIFY-COMPILE — 컴파일 체크 안내

직접 실행하지 않고 사용자에게 안내한다.

```
✅ 스캔 검증 완료 후 컴파일 체크를 실행하세요.

Unity 메뉴: Tools/H5/Compile Check
또는 배치모드:
  bash ~/github/h5-porting-workflow/templates/scripts/compile-check.sh PUREWEB
```

---

## 완료 후 채팅 출력 전 — 미해결 항목 확인

아래 항목 중 1건이라도 해당되면 AskUserQuestion 호출:

| 항목 | 발동 조건 |
|---|---|
| VERIFY-A | A_MISSING 1건 이상 |
| VERIFY-D | WebGL 비활성화 미처리 1건 이상 |
| VERIFY-VOCAB | 파일:라인 불일치 1건 이상, 또는 공통/Toss 전용 플레이스홀더 미채움 1건 이상 |
| VERIFY-STORAGE | 가드 누락 1건 이상 |
| VERIFY-RUNTIME | 라인 참조 오류 1건 이상 |
| VERIFY-VOID | CONTROL_FLOW·STATE_UNDEF 미처리 1건 이상 |

```
질문: "검증 완료 후 아래 항목이 미해결 상태입니다. 포팅을 진행할까요?"
  (미해결 항목 목록 나열)
옵션:
  - 확인 완료 — 포팅 진행합니다
  - 아직 확인 중 — 잠시 보류합니다
```

미해결 항목이 없으면 AskUserQuestion 없이 완료 메시지만 출력.

---

## 완료 후 채팅 출력

```
✅ porting-scan-verify 완료

📊 검증 결과
- VERIFY-A: 누락 N건 / CALLER_MISSING N건 / INTERNAL_UNGUARDED N건 / 이상 없음
- VERIFY-D: 미처리 N건 / 이상 없음
- VERIFY-BUILD-SCRIPT: 신규 발견 N건 / 이상 없음
- VERIFY-VOCAB: spot-check N건 중 불일치 N건 / 공통 플레이스홀더 미채움 N건 / Toss 전용 미채움 N건 / 빌드 씬 누락 N건
- VERIFY-STORAGE: 가드 누락 N건 / 이상 없음
- VERIFY-RUNTIME: 기록 정확 N건 / 라인 오류 N건 / 이미 처리됨 N건
- VERIFY-VOID: CONTROL_FLOW N건 / STATE_UNDEF N건 / 신규 발견 N건 / 이상 없음

NATIVE_BASELINE.md 교정: N건 | pureweb-checklist.md `## 이슈` 업데이트: N건

다음 단계: Tools/H5/Compile Check 실행
```
