AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: DESIGN_PROPOSAL
SOURCE_REFERENCE: ZIP folder 1; .png 20, .txt 1

# ML-CTX-001 상세 출처 검토 — 24/7 AI 거래 시스템 사례: 아키텍처와 안전 경계

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

사용자 원문 요청은 X에서 가져온 **24/7 AI 거래 시스템 구축 사례**의 MoneyLab 적용 가능성 평가였다. 첨부 20장은 `How to Build a 24/7 Trading System Using Claude Opus 5.5`라는 외부 사례의 시작부터 끝까지 이어지는 스크린샷으로 보인다. 외부 글이 제시하는 핵심은 **분석 LLM / 결정을 승인·거부하는 결정론적 위험관리 / 주문 집행**의 분리이며, 위험한 자동 실행을 최소화하는 것이다.

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. 전략 아이디어는 모델이 생성하되, 출력은 구조화된 thesis JSON/스키마로 검증하는 설계 예시.
2. 시장 헤드라인·웹페이지·뉴스를 불신 데이터로 취급하는 프롬프트 인젝션 차단 논의.
3. Paper-first, 주문 전 risk checks, stop-loss·포지션 제한·일일 손실 제한 등의 예시.
4. 주문 승인·거절·HOLD·오류를 남기는 audit journal, 시스템 종료를 위한 kill switch.
5. 연속 운영 loop와 호출 비용 절감을 위한 경량 모델·배치·이벤트 중심 아키텍처.
6. 외부 예제는 Alpaca 기반 주식 매매 코드를 포함하며 MoneyLab의 Upbit 인터페이스와 동일하지 않음.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. 대상: AI Supervisor를 비권위적 제안기로 유지하고, 별도의 결정론적 risk-policy와 paper executor 설계를 향후 검토.
2. 검증 전제: 실제 Upbit 공개 데이터의 타임스탬프·호가 가용성·비용 가정 확인; 승인된 실행 게이트가 없으면 LLM이 주문 권한을 갖지 않음.
3. MVP 최소 경로: Recorder → market state → approved strategy → paper fill → net PnL → guard/monitoring.

## 4. 반론·위험·제약

- 외부 예제 코드의 API 응답·수수료·약관·지원 자산 검증되지 않음.
- ‘24시간’ 운영이 수익성이나 장애 복구를 보장하지 않음.
- 현재 저장소의 실거래 금지와 충돌하지 않도록 목표 설계만 기록.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **20개 이미지 및 사용자 원문 프롬프트를 대조했으나 개별 코드 샘플의 정확성·동작은 미검증.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-001.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
