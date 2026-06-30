# [프로젝트명] Docs

프로젝트 루트의 문서 폴더. AI·개발자 공용 참고 및 포팅 산출물 보관용.

## 목적

- **개발 3원칙** 준수: 프레임워크 유지, 책임 분리, 기존 기능 재사용
- 개발 전 참고 문서로 계획 수립, 포팅 파이프라인 산출물 일괄 보관

## 문서 구성

| 문서 / 폴더 | 생성 시점 | 용도 |
|---|---|---|
| `FRAMEWORK_REFERENCE.md` | project-init | 개발 전 필수 참고. 진입점·시스템·유틸·헬퍼·재사용 API 요약(개조식) |
| `porting/PORTING_ANALYSIS.md` | porting-scan | SDK 목록·컴파일·런타임 이슈 분석 결과 |
| `porting/PORTING_VOCAB.md` | porting-scan | 포터 에이전트가 참조하는 메서드·클래스 어휘 사전 |
| `porting/compile_result.log` | CompileChecker | 플랫폼별 컴파일 체크 결과 |
| `porting/.stats/agent-stats.md` | 각 analyzer | 에이전트 실행별 히트/Zero-Hit 패턴 누적 기록 |
| `design/IAP.md` | iap-analyzer | IAP 상품 구성·PID·보상 역추적 |
| `design/IAA.md` | iaa-analyzer | 광고 Placement·보상·조건 역추적 |
| `design/데이터-저장-로드.md` | save-point-analyzer | 저장 시스템 구조 역추적 |

## 주의

- `FRAMEWORK_REFERENCE.md`는 개조식(요약)으로 유지해 토큰/Context 한계를 고려함.
- 코드를 변경했으면 영향 받는 문서를 반드시 갱신(죽은 문서 방지).
