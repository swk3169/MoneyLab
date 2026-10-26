# ERRATA: PUBLIC-RELEASE-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: PUBLIC-RELEASE-01-ERRATA-001
TASK_ID: PUBLIC-RELEASE-01
TARGET_WORK_ORDER: docs/tasks/PUBLIC-RELEASE-01/WORK_ORDER.md @ 52c857206c4e0d18e920e5d5bf6488646cc4e3c0 (sha256 07c245031a2184b886848cebe74778c417b708aa708e8d02b23b961216385e53)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER, 2026-10-26

## CHANGED_FIELDS

CHANGED_FIELDS:
- UNRESOLVED_PRE_IMPLEMENTATION_DECISIONS.U-A (MIT copyright holder/year)
- UNRESOLVED_PRE_IMPLEMENTATION_DECISIONS.U-B (`pyproject.toml` license metadata 표현)

## RATIONALE

RATIONALE:
- MIT는 D1에서 이미 선택되었다.
- 2026은 이번 public release에 선택된 copyright 연도다.
- Son Woo Kyu는 선택된 copyright holder 표시 이름이다.
- SPDX 문자열은 선택된 최소 license metadata 표현이다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- U-A: RESOLVED. LICENSE의 copyright 줄은 `Copyright (c) 2026 Son Woo Kyu`이다.
- U-B: RESOLVED. `pyproject.toml`의 `[project].license`는 SPDX 문자열 `license = "MIT"`를 쓴다.

## SCOPE

SCOPE:
- 이 ERRATA는 U-A와 U-B만 해소한다. Work Order의 다른 계약(USER_DECISIONS D1–D7, ALLOWED_FILES, PROTECTED_FILES, GATE_SEQUENCE, 감사·E2E·PR_CI·PREPUBLIC_AUDIT·VISIBILITY_CHANGE 계약 등)은 바꾸지 않는다.
- publication readiness는 여전히 NO다. PREPUBLIC_AUDIT와 VISIBILITY_CHANGE는 일어나지 않았다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
