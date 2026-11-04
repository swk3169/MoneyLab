AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-05
STATUS: REFERENCE_SNAPSHOT

CLAIM_LABEL: EXTERNAL_CLAIM
SOURCE_REFERENCE: 2026-11-05 supplied ZIP (source file private)

# MoneyLab 소스 레지스터 V2 (공개용 간략판)

> 사용자가 2026-11-05 제공한 ZIP의 자료와 GitHub `main` 문서를 대조한 **출처 기반 상세 검토 문서**이다. 외부 작성자의 주장은 미검증이며, 이 문서는 실행 지시·승인된 전략·수익 증거가 아니다. 전체 원본 사진·코드·논문은 이 문서에 포함하지 않는다.

## ZIP 수준 자료 구성 (개별 파일 이름·원본 파일은 비공개)

| 참조 그룹 | 총 파일 | 구성 | 공개 문서 링크 | 검증 상태 |
|---|---:|---|---|---|
| ZIP 001 | 21 | 20 screenshots, 1 user prompt | [001](reviews/ML-CTX-001_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 002 | 16 | 15 screenshots, 1 user prompt | [002](reviews/ML-CTX-002_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 003 | 1 | 1 user prompt only | [003](reviews/ML-CTX-003_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED (원본 자료 없음, prompt only) |
| ZIP 004 | 2 | 1 screenshot, 1 prompt | [004](reviews/ML-CTX-004_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 005 | 7 | 7 screenshots (6 economics; 1 alpha formula) | [005](reviews/ML-CTX-005_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 006 | 50 | 48 screenshots, 1 PDF (361 pages), 1 empty prompt | [006](reviews/ML-CTX-006_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 007 | 2 | 1 screenshot, 1 prompt | [007](reviews/ML-CTX-007_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| ZIP 008 | 2 | 2 screenshots | [008](reviews/ML-CTX-008_SOURCE_REVIEW.md) | SOURCE_DOCUMENTED |
| **합계** | **101** | **94 images, 1 PDF, 6 prompts** | 원본은 Git에 업로드하지 않음 | — |

원본 파일별 SHA-256 목록과 원본 ZIP은 Git 밖에서 사용자가 관리한다 (USER_MANAGED / NOT_IN_GIT). 새 PC에서 원본이 필요하면 사용자에게 요청한다. 위 수량은 V2 작성 시 집계이며 Claude Code는 원본 ZIP과 대조하지 않았다 (NOT_VERIFIED).

## 참조의 의미

ZIP 001~008 폴더명은 사용자 분류이며 GitHub ML-CTX-001~008의 내용과 완전 일치하지 않는다. 특히 ZIP 005/006, ZIP 007/003의 주제 교차가 있다. 자료의 원본 입수와 외부 주장 독립 검증을 구분한다.

## 검증 상태 정의

- `SOURCE_DOCUMENTED`: 원본 자료가 존재하고 주요 내용·한계를 기록함.
- `INDEPENDENTLY_VERIFIED`: 외부 또는 저장소 증거로 주장을 확인함 (현재 해당 없음).
- `IMPLEMENTED`: 저장소 코드·테스트 근거가 있음 (이 레지스터의 자료는 해당 없음).
