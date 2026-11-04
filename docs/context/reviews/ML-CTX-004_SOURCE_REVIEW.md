AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: DESIGN_PROPOSAL
SOURCE_REFERENCE: ZIP folder 4; .png 1, .txt 1

# ML-CTX-004 상세 출처 검토 — Context Engineering: 필요 시점의 최소 맥락 회수

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

Context Engineering 설명 이미지 1장과 사용자 요청 1개. 이미지에는 컨텍스트의 구성 요소, 도구 결과·장기 기억·선택적 검색, 더 나은 입력 구성이라는 고수준 개념이 시각화되어 있다. 개별 도식의 문구·수치의 독립 검증은 수행하지 않았다.

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. 전체 과거 대화를 통째로 항상 주입하기보다 active Work Order·관련 코드·근거만 단계별 제공.
2. 원본(raw), 요약, 현재 Git 상태, 승인된 실행 계약은 권위·신선도가 다르므로 분리.
3. Context pollution과 오래된 계획, 중복된 정보가 잘못된 작업 승인을 유도하는 것을 방지.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. `docs/context/README.md`를 독해 순서 색인으로 사용; 별도 새 권한 시스템을 만들지 않음.
2. 필요할 때 선택적으로 ML-CTX review를 불러오고 현재 HEAD·Gate는 매 세션 별도 확인.

## 4. 반론·위험·제약

- 긴 문서 자동 주입은 비용과 오류를 증가시킬 수 있음.
- 프롬프트 인젝션이 포함될 수 있는 외부 자료는 data-only로 사용.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **이미지 1개, 사용자 프롬프트 1개; 운영효과 실측 없음.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-004.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
