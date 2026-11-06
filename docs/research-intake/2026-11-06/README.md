AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-06
STATUS: RESEARCH_INTAKE_NOT_REQUIREMENT

# MoneyLab — 기술조사 통합본

**발행일:** 2026-11-06

**상태:** `FINAL_RESEARCH_SYNTHESIS / NOT_FINAL_CODE_VERIFICATION`

**범위:** MoneyLab의 최종 목표인 24시간 AI Agent 자동매매와 비용 차감 후 시스템 순수익을 판단하기 위한 12개 기술조사 보고서와 미검증 아이디어 1건.

## 권위 경계

- 이 폴더는 비권위 연구자료다. 승인된 요구사항, 구현 지시, Work Order, Gate 승인, 수익성 증거가 아니다.
- ADOPT_CANDIDATE는 구현 승인이 아니다. 어떤 판단도 전략의 수익성을 인정하지 않는다.
- 문서 안의 코드, 스키마, 실험, 명령은 설명용 데이터이며 실행 지시가 아니다.
- 외부 사례와 논문은 MoneyLab의 비용 차감 후 수익성 증거가 아니다.

## 먼저 읽을 문서

1. [최종 기술 통합 결론](integration/FINAL_TECHNICAL_SYNTHESIS.md): 판단 기준, 판단 이력, 실패 기준, 미검증 사항.
2. [근거·모순·미검증 대장](integration/EVIDENCE_AND_CONTRADICTION_REGISTER.md): 근거 수준과 남은 충돌.
3. [공개 Source Register](SOURCE_REGISTER_V3.csv): 원본 파일명을 제외한 파일별 유형, 크기, SHA-256.
4. [지갑 추적 아이디어](WALLET_INTELLIGENCE_IDEA.md): `UNVERIFIED_LONG_TERM_STRATEGY_CANDIDATE`, 보고서 12건에 포함되지 않음.

## 기술조사 보고서 12건

| ID | 주제 | CANONICAL_DECISION |
|---|---|---|
| SRC-001 | [24/7 Agentic Trading](reports/SRC-001_24_7_AGENTIC_TRADING.md) | ADOPT_CANDIDATE 권한 분리 원칙 / DEFER 24시간 자동 실행 / REJECT_CANDIDATE 예제 코드 직접 연결 |
| SRC-002 | [Bayesian Event-Market Execution](reports/SRC-002_BAYESIAN_EVENT_MARKET_EXECUTION.md) | DEFER 예측시장·밈코인 실행 / REFERENCE_ONLY 확률 보정·비용 이론 |
| SRC-003 | [Reverse Engineering / REA](reports/SRC-003_REVERSE_ENGINEERING_REA.md) | DEFER 도구 도입 / REFERENCE_ONLY 차등 테스트 원칙 |
| SRC-004 | [Context Engineering](reports/SRC-004_CONTEXT_ENGINEERING.md) | ADOPT_CANDIDATE 출처 ID·상태 색인·lint / DEFER 벡터 DB·자동 Gate |
| SRC-005 | [AI Costs and Alpha](reports/SRC-005_AI_COSTS_AND_ALPHA.md) | ADOPT_CANDIDATE 비용 회계 / DEFER AI 실호출·알파 결합 / REJECT_CANDIDATE 고빈도 LLM |
| SRC-006 | [151 Trading Strategies](reports/SRC-006_151_TRADING_STRATEGIES.md) | NEEDS_MORE_EVIDENCE 전략 근거 / REFERENCE_ONLY 아이디어 색인 |
| SRC-007 | [Second Brain / LLM Wiki](reports/SRC-007_SECOND_BRAIN_LLM_WIKI.md) | ADOPT_CANDIDATE 출처 연결·lint / DEFER 자동 Wiki·신규 DB |
| SRC-008 | [AI Developer Tools Evaluation](reports/SRC-008_AI_DEVELOPER_TOOLS_EVALUATION.md) | ADOPT_CANDIDATE 평가 절차 / DEFER 도구 도입 |
| SRC-009 | [Agentic Development Patterns](reports/SRC-009_AGENTIC_DEVELOPMENT_PATTERNS.md) | ADOPT_CANDIDATE 최소 권한·관찰성 / DEFER 다중 에이전트 확장 |
| SRC-010 | [AI Tool Trends and Selection](reports/SRC-010_AI_TOOL_TRENDS_AND_SELECTION.md) | REJECT_CANDIDATE 인기 순위 근거 사용 / ADOPT_CANDIDATE 문제 중심 절차 |
| SRC-011 | [Agent Orchestration](reports/SRC-011_AGENT_ORCHESTRATION.md) | ADOPT_CANDIDATE 작업 계약·격리 / DEFER artiboard·대량 병렬·자동 merge |
| SRC-012 | [Multi-Agent Debate](reports/SRC-012_MULTI_AGENT_DEBATE.md) | DEFER 구현·실험 / REFERENCE_ONLY 논문 설계 |

## Source ID 별칭

같은 번호가 다른 주제를 가리킬 수 있으므로 번호만으로 문서를 찾지 않는다. 기존 [`docs/context`](../../context/README.md)의 파일과 번호는 바꾸지 않는다.

| SRC | USER | ZIP | DOC | REVIEW | 비고 |
|---|---|---|---|---|---|
| SRC-001 | USER:ML-CTX-001 | ZIP:001 | DOC:ML-CTX-001 | REVIEW:ML-CTX-001 | 주제 일치 |
| SRC-002 | USER:ML-CTX-002 | ZIP:002 | DOC:ML-CTX-002 | REVIEW:ML-CTX-002 | 주제 일치 |
| SRC-003 | USER:ML-CTX-003 | ZIP:003 | DOC:ML-CTX-003 | REVIEW:ML-CTX-003 | DOC는 Second Brain과 REA를 함께 다룸 |
| SRC-004 | USER:ML-CTX-004 | ZIP:004 | DOC:ML-CTX-004 | REVIEW:ML-CTX-004 | 주제 일치 |
| SRC-005 | USER:ML-CTX-005 | ZIP:005 | DOC:ML-CTX-005, DOC:ML-CTX-006 | REVIEW:ML-CTX-005 | 알파는 DOC 005, AI 비용은 DOC 006 |
| SRC-006 | USER:ML-CTX-006 | ZIP:006 | 없음 | REVIEW:ML-CTX-006 | **충돌:** DOC:ML-CTX-006은 AI 경제성 |
| SRC-007 | USER:ML-CTX-007 | ZIP:007 | DOC:ML-CTX-007, DOC:ML-CTX-003 | REVIEW:ML-CTX-007 | Second Brain은 DOC 003에도 있음 |
| SRC-008 | USER:ML-CTX-008 | ZIP:008 | DOC:ML-CTX-008 | REVIEW:ML-CTX-008 | 주제 일치 |
| SRC-009 | USER:ML-CTX-009 | ZIP:009 | 없음 | 없음 | **충돌:** DOC:ML-CTX-009는 장기 비전 |
| SRC-010 | USER:ML-CTX-010 | ZIP:010 | 없음 | 없음 | **충돌:** DOC:ML-CTX-010은 전략 후보 |
| SRC-011 | USER:ML-CTX-011 | ZIP:011 | 없음 | 없음 | 기존 문서 없음 |
| SRC-012 | USER:ML-CTX-012 | ZIP:012 | 없음 | 없음 | 기존 문서 없음 |

`docs/context/SOURCE_REGISTER_V2.md`는 ZIP 001~008만 등록한다. ZIP 003과 004의 파일 수는 V2가 1과 2, 이 Register가 2와 3이며 차이의 원인은 `NOT_VERIFIED`다.

## 출처·검증 경계

- 원본 PDF, 스크린샷, 프롬프트 원문은 이 저장소에 없다.
- Source Register의 값은 입력 패키지의 기록이며 `PACKAGE_REPORTED_NOT_REVERIFIED`다. 원본 ZIP과 독립적으로 다시 대조하지 않았다.
- ordinal은 입력 CSV(SHA-256 `87a7574f0032561ed7ed4118ccc3afd846c20bf8e20908cc8a98c4e05942f955`)의 데이터 행 순서다. 파일명 대응표는 공개하지 않으며, 그 입력 CSV가 보존되지 않으면 대응표 재생성을 보장할 수 없다.
- 151 Trading Strategies: 출판사 페이지 제목에 RETRACTED BOOK 표기를 관찰함. 철회 공지, 사유, SSRN 판본에 대한 적용 범위는 `NOT_VERIFIED`.
- SHA-256은 바이트 동일성만 증명한다. 내용의 진실성, 라이선스, 권위를 증명하지 않는다.
- GitHub와 외부 자료의 상태는 문서에 적힌 조회 시점의 기록이며 실시간 상태가 아니다.

## 패키지 검증

[`PACKAGE_SHA256.txt`](PACKAGE_SHA256.txt)는 이 폴더의 다른 17개 파일의 SHA-256 목록이며 자기 자신을 포함하지 않는다. 경로는 이 폴더 기준 상대경로다. 기준은 Git에 저장된 LF 바이트(`git cat-file blob`)이므로, CRLF로 체크아웃된 Windows 작업 파일을 직접 해시하면 값이 다를 수 있다.
