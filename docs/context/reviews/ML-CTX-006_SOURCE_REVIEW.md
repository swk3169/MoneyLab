AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: EXTERNAL_CLAIM / RESEARCH_HYPOTHESIS
SOURCE_REFERENCE: ZIP folder 6; .jpg 1, .pdf 1, .png 47, .txt 1

# ML-CTX-006 상세 출처 검토 — 151 Trading Strategies + AI 구현 해설: 대용량 혼합 자료

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

ZIP의 006 폴더에는 이미지 48개, 361쪽 PDF 1개, 빈 프롬프트 파일 1개가 있다. PDF는 **Zura Kakushadze 및 Juan Andrés Serur, _151 Trading Strategies_, 2018-08-17 표기**를 포함한다. 그 외 사진은 외부 게시자가 책의 전략 5개를 추려 코드·프롬프트·검증방법·추가 전략 분류를 해설한 글이다. **책 자체와 제3자의 구현 예제를 분리해서 인용해야 한다.**

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. 원문 PDF 표지/목차 기준: 주식, 옵션, ETF, 파생, 외환, 암호화폐 등 여러 자산에 걸친 전략·수식을 기술하는 교육용 자료.
2. 외부 스크린샷의 다섯 후보: Hodrick–Prescott filter 기반 추세, k-nearest neighbors 예측, ANN quantile, 통계적 차익거래/분산배분, X 게시물 기반 감성/베이지안 추정.
3. 스크린샷에는 알파 결합(regression residualization), Crypto strategy skeleton, Gate/리스크 검사 예시 등이 포함.
4. 스크린샷에 나온 파이썬 코드는 외부 설명의 예시로, 의존성·데이터 시점·라이브러리 인터페이스와 정확성을 검증하지 않았음.
5. 일부 구현 예시(HP trend, KNN, ANN, social X feeds)는 상대적으로 미래 누수·트레이닝 분할·데이터 비용·수집권한 위험이 큼.
6. 다중 알파 결합 전 전략별 실거래 비용 차감 검증·다중검정 및 1회 holdout 규칙을 적용해야 함.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. 즉시 구현하지 말고 BTC spot long/cash에 부합하는 후보만 연구 우선순위로 선정.
2. 가장 먼저 단순 추세/반전과 buy-and-hold/cash의 비용 차감 비교; 이후 KNN 등 복잡한 전략은 기준선 초과 증거 요구.
3. X 감성 자료는 라이선스, 수집 정책, 정량 레이블, 신호 발생 시각 증거가 없으면 미적용.
4. 외부 코드에서 출발하기보다 기존 Backtest 및 data contracts에 맞춘 별도 WO와 deterministic 테스트.

## 4. 반론·위험·제약

- PDF 저작권 표기 `All Rights Reserved`. GitHub 공개 저장소에 전체 PDF·원본 이미지·장문 발췌를 재배포하지 말 것.
- 스크린샷은 교육 콘텐츠이므로 코드 성공과 거래 수익을 입증하지 못함.
- 모델 선택·하이퍼파라미터 탐색·데이터 스누핑과 자산시장 미스매치 위험.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **48개 이미지, 361쪽 PDF 표지 및 목차/관련 페이지 확인, 프롬프트 1개(빈 파일). 361쪽 전체 수식의 정확성을 완전 감사한 것은 아님.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-006.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
