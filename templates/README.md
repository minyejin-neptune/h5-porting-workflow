# [프로젝트명] Docs

프로젝트 루트의 문서 폴더. AI·개발자 공용 참고 및 포팅 산출물 보관용.

## 목적

- **개발 3원칙** 준수: 프레임워크 유지, 책임 분리, 기존 기능 재사용
- 개발 전 참고 문서로 계획 수립, 포팅 파이프라인 산출물 일괄 보관

> 📚 HyperLane SDK 매뉴얼: https://github.com/neptunez-dev/hyperlane-sdk/tree/main/docs/manual

## 문서 구성

| 문서 / 폴더 | 생성 시점 | 용도 |
|---|---|---|
| `FRAMEWORK_REFERENCE.md` | project-init | 개발 전 필수 참고. 진입점·시스템·유틸·헬퍼·재사용 API 요약(개조식) |
| `porting/NATIVE_BASELINE.md` | porting-scan | 포팅 전 네이티브 불변 스냅샷 — 외부 SDK 목록·프로젝트 정보·게임 구조 (scan-verify 후 동결) |
| `porting/.sdk-list.md` | sdk-list-analyzer | 외부 SDK 목록 임시 산출(숨김 파일) — porting-scan이 수용해 NATIVE_BASELINE에 기재한 뒤 삭제 |
| `porting/pureweb-checklist.md` | porting-scan | 기반 작업목록(가변) — 기반 포팅 이슈(컴파일·런타임·공백)·확인 필요·기획자 보고·교정 기록·빌드 기록. 단계 진행 표는 pureweb-porter가 추가 |
| `porting/toss-checklist.md` | porting-scan | 토스 전용(배너·프로모션 등) 작업목록(가변) — 기획자 보고·교정 기록·빌드 기록. 기반 이슈는 pureweb-checklist 읽기 참조, 단계 진행 표는 toss-porter가 추가 |
| `porting/platform-checklist.md` | platform-porter (최초 실행 시 자체 생성) | HLSDK 공통(로그인·광고·IAP·저장·랭킹·햅틱·공유 등) 작업목록(가변) — platform-porter가 생성·관리, toss 등 개별 플랫폼 포터의 선행 조건 |
| `porting/PORTING_VOCAB.md` | porting-scan | 포터 에이전트가 참조하는 메서드·클래스 어휘 사전(위치 인덱스) |
| `porting/compile_result.log` | CompileChecker | 플랫폼별 컴파일 체크 결과 |
| `porting/.stats/agent-stats.md` | 각 analyzer | 에이전트 실행별 히트/Zero-Hit 패턴 누적 기록 |
| `design/IAP.md` | iap-analyzer | IAP 상품 구성·PID·보상 역추적 |
| `design/IAA.md` | iaa-analyzer | 광고 Placement·보상·조건 역추적 |
| `design/데이터-저장-로드.md` | save-point-analyzer | 저장 시스템 구조 역추적 |

## 주의

- `FRAMEWORK_REFERENCE.md`는 개조식(요약)으로 유지해 토큰/Context 한계를 고려함.
