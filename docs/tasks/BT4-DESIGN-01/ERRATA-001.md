# ERRATA: BT4-DESIGN-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-DESIGN-01-ERRATA-001
TASK_ID: BT4-DESIGN-01
ERRATA: 001
TARGET_WORK_ORDER: docs/tasks/BT4-DESIGN-01/WORK_ORDER.md @ 55a834947c4145e80dacc39659bdc4b47588bbe4 (sha256 4207775f54f533fd0743b2dae665555b8103771e46372e978c71888261bc8303)
CANONICAL_BASE_SHA: 2a184b2d3f44d868590d65f85f7dfd9d09fe7988
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## CHANGED_FIELDS

CHANGED_FIELDS:
- SCOPE_INVENTORY / ALIASES_AND_LINKS의 연결 관계 한 줄 (Work Order 114행 "D9(H_end) ↔ 위험 정책 confirmation interval")

UNCHANGED_FIELDS: 위 한 줄을 제외한 Work Order의 모든 조항은 그대로다.

## REASON

REASON: IMPLEMENTATION gate에서 canonical repository(CANONICAL_BASE_SHA)를 다시 확인한 결과, Work Order의 연결 관계 "D9(H_end) ↔ 위험 정책 confirmation interval"을 지지하는 근거가 없었다. 이 ERRATA는 그 사실 관계 하나를 canonical source에 맞게 정정한다.

## INCORRECT_ORIGINAL_RELATIONSHIP

INCORRECT_ORIGINAL_RELATIONSHIP: D9(H_end) ↔ 위험 정책 confirmation interval (Work Order 114행). 이 관계는 폐기한다.

## CORRECTED_CANONICAL_RELATIONSHIPS

CORRECTED_CANONICAL_RELATIONSHIPS (서로 별개의 두 관계):
1. D9(H_end) ↔ holdout length
2. 위험 정책 confirmation interval ↔ public boundary C

## CANONICAL_EVIDENCE

CANONICAL_EVIDENCE (모두 CANONICAL_BASE_SHA 기준, GIT_VERIFIABLE):
- 관계 1:
  - `docs/research_v06_preregistration_draft.md:208`: historical holdout 구간은 "2024-04-01 ~ H_end (18절 결정 D9: 2026-10-02 또는 동결일 전날)"이다.
  - `docs/research_v06_preregistration_draft.md:527`: D9는 historical holdout 끝 H_end의 선택이다.
  - `src/moneylab/research/v06/montecarlo.py:162`: `holdout: int = 914  # 2024-04-01 .. 2026-10-02 (D9)`
- 관계 2:
  - `docs/tasks/BT-3E/WORK_ORDER.md:259`: confirmation interval은 BT4_FROZEN_VALUE 필드 `confirmatory_first_day`, `confirmatory_last_day`다.
  - `docs/tasks/BT-3E/WORK_ORDER.md:204`: "확증 엔진 구간의 G_end(= confirmatory_last_day + 3일)는 public 경계 C 이하여야" 한다.
  - `docs/tasks/BT-3E/WORK_ORDER.md:306`: T12 "confirmatory_last_day + 3일 > C이면 정책 기록을 거부한다."
- 두 관계가 별개인 근거:
  - `docs/research_v06_preregistration_draft.md:207-208`: 확증 평가 구간은 "warmup 끝 ~ 2024-03-31"이고, H_end는 그 뒤 historical holdout(2024-04-01 ~ H_end)의 끝이다.

## NORMATIVE_EFFECT

NORMATIVE_EFFECT:
- Work Order의 잘못된 연결 관계 "D9(H_end) ↔ 위험 정책 confirmation interval"을 폐기한다.
- 이를 CORRECTED_CANONICAL_RELATIONSHIPS의 두 관계로 대체한다.
- 이후 gate에서는 정정된 관계를 Work Order의 규범적 해석으로 쓴다.

## NON_EFFECTS

NON_EFFECTS: 이 ERRATA는 다음을 하지 않는다.
- D9 값, H_end, confirmation interval 값, 위험 정책 값의 결정
- 새로운 dependency의 생성
- validation requirement의 변경
- 절차 선택
- D1–D10, U, G, DP2–DP4, BT4-Q18의 결정
- `docs/bt4_design_01.md` 내용의 변경

어떤 decision value도 고정하지 않는다.

## DELIVERABLE_STATUS

DELIVERABLE_STATUS: IMPLEMENTATION gate에서 작성한 `docs/bt4_design_01.md`(sha256 34b73441c2016d9229617f1a8c83266087b848498c28b4e3a843430e6b243f34)는 이미 canonical 관계를 따른다(§2.10). 이 ERRATA 때문에 산출물을 고치지 않는다.
