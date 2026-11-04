AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: DESIGN_PROPOSAL
SOURCE_REFERENCE: 2026-11-05 user conversation + existing ML-CTX-001..008 + diagrams/ML-CTX-009-A..C (SOURCE_CANDIDATE)

# ML-CTX-009 — MoneyLab 장기 비전 및 Agentic AI Trading System

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.

## 1. 한 문장 비전

MoneyLab의 **미래 목표**는 24시간 시장을 감시하는 AI 에이전트가 비용 차감 후 검증된 거래 기회를 탐색·평가하고, AI와 분리된 결정론적 위험·실행 계층이 별도 승인된 운용 조건 안에서만 주문을 처리하며, 위험 통제와 재현가능한 성과 계측을 통해 **위험 조정 순수익을 추구하는** 자율 트레이딩 시스템이다. **수익은 미검증이며 보장되지 않는다.**

### Current vs future

| 영역 | 현재 상태 확인 출처 | 장기 비전 (모두 PLANNED / NOT_APPROVED) |
|---|---|---|
| Market data | `README.md`, `ARCHITECTURE.md` | 24/7 수집·장애 복구·품질 모니터링 |
| Replay/Backtest | 현재 구현(실거래 전략 이익 증거 없음) | 비용·시장 영향·누수 감사 기반 승인된 전략 레지스트리 |
| Knowledge/Supervisor | read-only proposal 생성 | AI 연구 워크플로·기회 발견·자율 평가 |
| Risk | paper kill switch 등 일부 구성요소 | 결정론적 portfolio risk limits·중복주문 방지·kill switch |
| Paper | 일부 오프라인 기능 | 실시간 가상 체결 + 재현 가능한 ledger/PnL |
| On-chain | 없음 | 공개 주소의 거래·흐름 분석; 지갑 연결 금지 |
| Live | **NOT_IMPLEMENTED / NOT_AUTHORIZED** | 별도 사용자 승인·실거래 한도·보안 검증 이후에만 가능 |

현재 구현 여부의 단일 근거는 이 스냅샷이 아닌 해당 시점의 Git, README, ARCHITECTURE, 테스트 및 Work Order이다.

## 2. 에이전트 역할 (향후 설계 후보)

| Agent/Layer | 책임 | 권한 경계 |
|---|---|---|
| Market Scanner & State Analyzer | 시장 상태·데이터 신선도·유동성 추정 | 읽기 및 비권위 신호 |
| Wallet Intelligence Agent | 공개 온체인 거래를 가설/특징량으로 변환 | 키·지갑 연결·대리주문 없음 |
| Opportunity Discovery Agent | 사전 등록 가능한 신호 후보 발굴 | 승인 전략으로 자동 승격 금지 |
| Research Supervisor | Work Order/검증 질문 제안 | 기존 read-only Supervisor 범위 밖은 별도 승인 |
| Strategy Selection Agent | 승인된 전략 후보의 선택 정책 제안 | 주문 권한 없음 |
| Performance Review Agent | 비용 차감 손익·드리프트·실패 원인 진단 | 자동 self-rewrite/위험 한도 상향 금지 |
| Deterministic Risk/Execution | 가용 자본·한도·중복·중단·주문 조건 확인 | 추후 독립 게이트·별도 명시적 승인 |

## 3. 수익 판단 기준

- `Net Trading PnL = Realized/Marked Gross PnL - fees - spread - slippage - 기타 직접 거래 비용` (모델·데이터 정의 확인 필요).
- `Net System PnL = Net Trading PnL - 모델 호출료 - 데이터료 - 서버 운영비 - 기타 운영비`.
- 위험: MDD, tail losses, 실패 모드, 실행 품질, 거래 중단·복구, 총 소액 계좌 손실 한도.
- 검증: 사전등록, 타임스탬프·현시점 정보만 사용, sealed split 1회 사용, OOS/forward, paper fill 차이, 다중검정 제어.
- 합성 데이터와 외부인의 성과 주장은 수익성 증거가 아님.

## 4. 도식도 보존

세 Mermaid 설계 후보는 `docs/context/diagrams/`에 별도 파일로 보존하는 방안을 제안한다.
[A: 최종 Agentic 시스템](diagrams/ML-CTX-009-A_SOURCE_CANDIDATE.md) / [B: 24시간 Paper MVP](diagrams/ML-CTX-009-B_SOURCE_CANDIDATE.md) / [C: PC·세션 복원](diagrams/ML-CTX-009-C_SOURCE_CANDIDATE.md). 출처가 독립 검증되지 않은 `SOURCE_CANDIDATE`이며 채택된 설계나 현재 구현 상태가 아니다. 개선 설계는 원본을 덮어쓰지 말고 별도 문서에 기록한다.

## 5. 수직 통합 MVP 우선순위 (DESIGN_PROPOSAL)

1. 기존 Recorder/Replay에서 실제 데이터 계약·거래비용·시간정합성 확인.
2. 최소 1개 사전 정의된 기준 전략을 deterministic risk + paper fill + ledger + net cost PnL에 연결.
3. 24/7 운영 지표: stale-data halt, duplicate-event idempotency, restart recovery, kill switch, 비용 상한, 실패 알림.
4. AI 에이전트는 읽기 전용 탐색 및 성과 리뷰부터 붙이고, 자동 실행 권한은 미래 단계로 분리.
5. Wallet Intelligence는 전략 후보이되, 기존 MVP의 필수 블로커가 아니다.

## 6. 의사결정과 보안 경계

`CLAUDE.md`, `docs/tasks/`, accepted ERRATA, knowledge records가 권위를 갖는다. 본 문서는 아이디어 및 중장기 설계의 기억만 보존한다. 해당 내용이 구현·거래·승인 의사가 됐다는 의미는 아니다.
