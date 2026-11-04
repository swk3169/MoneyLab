AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: EXTERNAL_CLAIM / RESEARCH_HYPOTHESIS
SOURCE_REFERENCE: ZIP folder 2; .png 15, .txt 1

# ML-CTX-002 상세 출처 검토 — Daniro/QuantumOrb: 뉴스→확률→가격괴리→체결 연구

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

15장의 이미지에는 뉴스 신호를 확률 추정치로 바꾸고 시장 호가와 비교하여 기회를 찾는 외부 사례, 베이즈 업데이트·순기대값·시장 간 불일치·체결 지연·자금배분 설명, 그리고 QuantumOrb 관련 게시글이 포함된다. **게시물 속 수익률은 제3자 주장**일 뿐이다.

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. 뉴스/이벤트를 가격 방향 단정이 아니라 확률 변화에 대한 관측치로 취급.
2. 사전 확률과 조건부 likelihood를 결합하는 베이즈 갱신 예시.
3. 내부 추정 확률과 거래 가능한 호가 사이의 격차에서 수수료·슬리피지 등을 제외하고 net edge 추정.
4. 하나의 사건에 연결된 여러 시장의 확률 합, 상호 배타적 결과의 일관성, correlated opportunities 점검.
5. 발견→주문 완료 간 지연, stale quote, 유동성·재고 리스크 및 켈리 비중 오용 주의.
6. QuantumOrb 관련 게시물은 신규 토큰 활동, 지갑 흐름과 거래 기록을 이용한다는 외부 설명을 포함.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. MoneyLab의 일봉 BTC long/cash에 확률모델이 곧바로 수익성을 주는 것은 아니므로 별도 사전등록 대상으로 유지.
2. 포지션 크기 판단은 제안된 확률의 calibration/Brier score/log loss/실행가능 호가로 검증해야 함.
3. Polymarket HTTP 451 제약을 우회하는 기능이나 실행 방법은 연구 적용 대상에 넣지 않음.
4. 공개 온체인 이벤트는 별도 Wallet Intelligence 연구 후보로 연동 가능하나 독립된 데이터 파이프라인이 필요.

## 4. 반론·위험·제약

- 게시물의 수익 수치·속도·모델 성과는 독립 증거가 없음.
- Solana 토큰/예측시장과 Upbit BTC 현물은 거래비용·상품구조·결과 라벨이 다름.
- 지갑 공개 관측값은 실제 순손익·전체 포지션을 의미하지 않음.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **15개 이미지와 사용자 프롬프트(QuantumOrb URL 포함) 검토. 외부 GitHub 저장소의 실제 코드는 미검증.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-002.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
