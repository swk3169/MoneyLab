AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: RESEARCH_HYPOTHESIS / EXTERNAL_CLAIM
SOURCE_REFERENCE: ZIP folder 5; .jpg 1, .png 6

# ML-CTX-005 상세 출처 검토 — Alpha 결합과 AI 에이전트 호출비 — ZIP 주제 혼합

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

ZIP의 005 폴더는 **동일 주제 자료만 들어 있지 않다.** 이미지 6개는 `Your AI Trading Agent Has a Salary`로 AI 호출비·연간 비용·소액 계정 손익분기점에 관한 외부 글이고, JPG 1개는 `A Unified Framework for Alpha Extraction and Signal Combination` 수식 이미지다. GitHub 005는 알파 결합, 006은 에이전트 경제성을 설명하므로 폴더=기존 문서의 1:1 대응이 아니다.

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. 외부 호출비 사례: 모델별 호출단가·트래픽·초기자금에 따른 기회비용 예시. 제시된 특정 가격과 샤프 비율은 현 시점 공식 가격·실증 성과가 아님.
2. LLM을 5분마다 항상 호출하는 설계보다 cheap screening/event-driven escalation으로 비용을 억제하자는 아이디어.
3. 알파 정규화/잔차화/공분산·위험조정 가중치 결합을 보여주는 공식 이미지; 출처·대상 시장·실증 결과 미검증.
4. 가중치가 전략 선택 시점까지 알려진 정보만 사용해야 함. 전체 기간 표준화 또는 미래 수익률로 훈련할 경우 누수 발생.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. 성과 지표를 `Net Trading PnL`과 `Net System PnL`로 구분, 365일 가동 비용 포함.
2. 알파 결합은 복수의 독립적으로 검증된 net signal 확보 전에는 후순위. BTC 현물 long/cash에서는 공매도/횡단면 중립 가정 불일치.

## 4. 반론·위험·제약

- 외부 기사의 수치·단가·결과는 예시이며 현재 공식 가격으로 간주하지 않음.
- 암호화폐 24/7 가동에 연 252거래일 가정을 그대로 적용하면 과소평가 가능.
- 합성 백테스트에서 여러 알파를 결합한 결과를 실거래 성능으로 오인 금지.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **이미지 7개; 사용자 프롬프트 없음. 005 폴더가 005 및 006의 주제를 교차 포함.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-005.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
