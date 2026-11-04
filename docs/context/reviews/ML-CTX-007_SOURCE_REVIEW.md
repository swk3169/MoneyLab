AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: DESIGN_PROPOSAL / EXTERNAL_CLAIM
SOURCE_REFERENCE: ZIP folder 7; .png 1, .txt 1

# ML-CTX-007 상세 출처 검토 — LLM Wiki 및 Second Brain 원본의 실제 위치

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.


## 1. 원본 자료와 실제 범위

이번 ZIP의 007 폴더에는 `SECOND BRAIN ARCHITECTURE` 이미지 1개와 사용자가 제공한 `LLM Wiki` 설명 프롬프트 1개가 있다. 두 자료가 동일 출처인 것은 아니다. 사용자가 쓴 100개 문서·40만 단어·10~15개 연관 페이지 수정 등의 수치는 독립 검증되지 않았다.

## 2. 기존 요약에서 놓치기 쉬운 핵심 내용

1. Second Brain: 원본 자료→구조화된 노트·링크→검색 및 결과물로 이어지는 지식 체계의 시각적 제안.
2. LLM Wiki 텍스트: Ingest(원본 기반 요약/위키 갱신 제안), Query(출처 기반 검색), Lint(모순·고아 페이지 검사) 컨셉.
3. 사용자 텍스트는 LLM이 wiki 파일을 자동 수정한다는 외부 주장을 포함하나 MoneyLab에서는 Work Order와 승인 경계를 우선.

## 3. MoneyLab 적용성 — 제안 / 미승인

1. Raw source는 불변; `docs/context`는 NON_AUTHORITATIVE; `knowledge/records`만 기존 승인 절차로 승격.
2. 자동 수정 대신 리뷰 가능한 diff 제안과 명시적 승인 후 문서 변경.
3. 새 PC에서 재현가능한 색인·출처·SHA 기록과 최신 Git/WO 검증 병행.

## 4. 반론·위험·제약

- 원본 게시자·저자와 구체적인 성능·규모 검증 필요.
- auto-edit 로직을 CLAUDE.md/Work Order/ERRATA에 연결하면 권한 혼동 발생.

## 5. 검증 결과 및 누락 상태

- 확보 자료: **이미지 1개, 사용자 원문 프롬프트 1개; 외부 원문 URL 없음.**
- 외부 자료의 수익·시장 성과: `EXTERNAL_CLAIM / NOT_VERIFIED`.
- 채택·구현·실거래 승인: `NONE`.
- 공개용은 간접 인용과 출처 연결만 허용; 원본 파일의 보존은 별도 비공개 저장/접근 통제 대상.
- ZIP의 폴더 번호와 기존 GitHub ML-CTX 번호는 주제 1:1 대응을 보장하지 않는다. 특히 003/005/006/007에 교차 배치가 있다.

## 6. 기존 문서 연결

- 기존: `docs/context/ML-CTX-007.md` (수정 금지 / 역사적 스냅샷)
- 상위: `docs/context/MASTER_CONTEXT_2026-10-30.md` (수정 금지).
- 관련: `docs/context/ML-CTX-009.md`, `docs/context/ML-CTX-010.md` (미래 목표/전략 후보 문서).
- 실제 현재 상태·승인은 `README.md`, `ARCHITECTURE.md`, Work Order 및 Git에서 새로 확인한다.
