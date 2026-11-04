AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: RESEARCH_HYPOTHESIS
SOURCE_REFERENCE: 2026-11-05 user-supplied ZIP + conversation; not approved

# ML-CTX-010 — 수익 전략 후보 및 원본 자료 연계

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.

## 1. 전략 후보 레지스터 (비권위)

| 후보 | 원본 근거 | 현재 증거 | 비용/주요 제약 | 제안된 후속 평가 |
|---|---|---|---|---|
| Upbit KRW-BTC 일봉 추세 long/cash | 사용자 연구 방향, 기존 prereg 초안 | 순수익 미검증 (v0.6 사전등록 초안, 미고정) | 수수료·스프레드·슬리피지·변동성 | 단순 benchmark, OOS, paper |
| Upbit 일봉 반전 long/cash | 사용자 연구 방향 | 미검증 | 과최적화·turnover | 전략별 prereg + net |
| 1~30초 호가 불균형 | v0.4 | **REJECT after costs** (`README.md` Current Project Status; 단일 6시간 세션) | 높은 왕복 비용 | 기각 사실을 부정하지 않음 |
| 베이지안 뉴스 확률/마켓 dislocation | ML-CTX-002, ZIP 002 | 외부 가설 | 시간 순서, fair probability, 호가체결, venue 제약 | 별도 계량 연구 후보 |
| HP Filter / KNN / ANN quantile | 151 Trading Strategies PDF + ZIP 006 외부 해설 | 수식/예제 ≠ 수익 증거 | 미래누수, 모델 선택, 시계열 CV | 축소된 단일 기준선 비교 후 검토 |
| StatArb / alpha combos | ML-CTX-005 + ZIP 005/006 | 설명 자료 | 다종목/공매도 필요, BTC long/cash와 불일치 | 별도 시장 가정 정리 |
| X 게시물 감성 | ZIP 006 외부 해설 | 미검증 | API 사용정책, 수집비용, 라벨 지연 | 소스 검증부터 |
| **On-chain high-performing wallet behavior** | 사용자 직접 아이디어 (2026-11-05 대화) | **RESEARCH_HYPOTHESIS / NOT_IMPLEMENTED** | PnL 부정확성, 거래 후 공개 지연, MEV, 가스, 생존자 편향, 여러 주소·CEX | read-only feature research |
| Multi-agent strategy selection | ML-CTX-001/009 | 설계 제안 | 과적합·선택 편향·AI 호출료 | 먼저 고정 정책 비교 |

## 2. 온체인 Wallet Intelligence 연구 가설

1. 공개 주소별 트랜잭션, DEX 스왑, 토큰 이동, 보유 기간 및 시점별 유동성에서 **반복 가능한 행동 특징량**을 계산할 수 있는가?
2. 높은 과거 수익률 지갑을 선택할 때 사후선택/생존자 편향, 자산 이동·다중 지갑의 PnL 누락, 이벤트 시점 가용성이 어떻게 영향을 주는가?
3. 관측 지연, 가스, 스프레드, 수수료, 슬리피지, 체결 실패를 차감해도 복제가능 신호가 남는가?
4. 주소와 실명 연결, 사적 개인 식별, 키 사용, 지갑 연결, 자동 추종 주문은 이 단계 범위 밖이다. 특정 지갑 주소·식별자는 이 공개 저장소에 기록하지 않는다.
5. 공개 데이터 **읽기** 역시 신규 provider 계약·응답 스키마·개인정보 위험 검토·독립 Work Order가 필요하다.

## 3. Polymarket vs. Upbit 배경

- Polymarket: 초기 에이전트 수익모델 검토의 일환이지만 개발 환경에서 HTTP 451 접근 제약이 보고됨. 우회 실행은 연구 범위 밖.
- Upbit: 공개 REST/WebSocket 기반 BTC 데이터·리플레이 경로가 기존 프로젝트와 직접 맞닿아 있음.
- 둘의 fee schedule, 포지션, 결제, latency, 자산·시장 데이터가 달라 상대 수익 우위는 검증되지 않았다.

## 4. 151 Trading Strategies 서지 및 출처 경계

- 원본 PDF(SSRN 3247865) 표지 기준 (V2 작성자 확인, Claude Code 미검증): **Zura Kakushadze & Juan Andrés Serur, _151 Trading Strategies_, August 17, 2018**. 361 PDF pages; PDF에는 2018년 저작권 고지가 있다.
- 표지·목차 일부와 전략 사례를 확인했으나 전 361쪽의 정확성·전략별 순수익을 검증한 것은 아니다.
- PDF 자체의 수학식과 X 게시물 작성자의 코드·설명은 **서로 다른 출처**다. 외부 코드 예제를 원저자의 공식 코드 또는 검증된 백테스트로 표기하지 않는다.
- PDF와 원문 스크린샷은 공개 Git 저장소에 포함하지 않는다. 저작물 재배포 여부는 별도 권리 검토.

## 5. 절차상의 증거 상태

`EXTERNAL_CLAIM` ↔ `RESEARCH_HYPOTHESIS` ↔ 사전등록된 실험 ↔ 검증된 코드/결과 ↔ PAPER_CANDIDATE 는 자동 승격 규칙이 아니다. 승인·Gate는 Work Order와 기존 Knowledge Schema로만 관리한다. **REFERENCE ≠ REQUIREMENT.**
