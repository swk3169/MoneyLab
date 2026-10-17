# ERRATA: MC-V06 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: MC-V06-ERRATA-001
TASK_ID: MC-V06
TARGET_WORK_ORDER: docs/tasks/MC-V06/WORK_ORDER.md @ 4fd4d2d08bb092ceb726e93327fba5b73432a993 (sha256 3789082b6a012e8e1fc372f6a8a84cc4c82d07465bf7e70d2721b668ed40e2d4)
CI_IMPLEMENTATION_COMMIT: 4081c5d0dfbee34abf219b03a0d91b73f3688c45 (tree e977213f1d7e7ff9b818251598e7c8db7c455b04; 이 ERRATA는 Ci를 대체하지 않는다)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## CHANGED_FIELDS

CHANGED_FIELDS:
- NO_RESUME_FEATURE (해석 명확화 추가, 기존 문장 유지)
- ALLOWED_ACTIONS.MC_FULL_RUN (실행 단위 정의 추가)
- ARTIFACT_PROVENANCE_CONTRACT (전체 실행 산출물의 정의 추가)
- PROCEDURE_ACCEPTANCE.MC_FULL_RUN (단위 집합 기준 적용)
- PROCEDURE_ACCEPTANCE.MC_RESULT_AUDIT (구조 집계 감사를 과학 해석 앞에 추가)
- STOP_CONDITIONS (단위 실행 정지 조건 추가)
- 새 절: PROVENANCE_TERMS
- 새 절: MC_FULL_RUN_UNIT_CONTRACT

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): R_OUTER = 10,000, B_BOOT = 9,999, K_RAND = 9,999, TRUTH_YEARS = 400, TARGET_MAX_MC_SE = 0.005, ADAPTIVE_STOPPING = PROHIBITED, 시나리오 정의·개수·순서, seed(20261012)와 파생 seed 규칙, 과학 절차, 판정 규칙, 위험 의미, 시뮬레이션 달력, 산출물 스키마 `moneylab.research_v06_sim/2`, 구현 코드, 통계 해석, GATE_SEQUENCE, ALLOWED_FILES, PROTECTED_FILES.

## RATIONALE

RATIONALE: MC_PILOT(OPTION_B, Ci 4081c5d, SYNTHETIC / NOT_EVIDENCE / ENGINEERING_PILOT_ONLY)의 공학 추정은 규범 전체 실행을 한 번의 `write_study()` 호출로 하면 12 worker에서 약 8–8.5일의 연속 실행이 필요하다는 것이다(측정 시나리오 2/18, ENGINEERING_ESTIMATE). 현재 `write_study()`는 `execution.json`과 `SHA256SUMS`를 모든 시나리오가 끝난 뒤에만 쓰고 기존 디렉터리를 이어 쓰지 않으므로, 중간 실패 하나가 전체 실행을 잃게 한다(실패 영역 ≈ 8일). 사용자는 과학 구성을 바꾸지 않고 실패 영역만 줄이는 것으로 결정했다. 계약 검토(READ_ONLY_INVESTIGATION)는 다음을 확인했다: 모든 난수 흐름은 `derived_seed(seed, *parts)`로 기본 seed, 시나리오 이름, 반복 번호, 결정적 내부 태그에서만 파생되고, 시나리오 목록 위치, 다른 시나리오의 존재, worker 수, 벽시계 상태에 의존하지 않는다. 시나리오 사이에 공유 상태가 없다. 따라서 시나리오 하나만으로 호출한 `write_study()`의 `scenarios/<name>/summary.json`과 `records.jsonl`은 같은 구현·설정·Python·seed에서 단일 호출의 해당 시나리오와 바이트가 같다고 기대된다. 이 ERRATA는 MC_FULL_RUN을 시나리오별 독립 규범 단위 18개로 실행하는 방법과 그 감사 기준만 정한다. 코드·스키마·과학 값을 바꾸지 않는다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- PROVENANCE_TERMS (새 절):
  - CI_IMPLEMENTATION_COMMIT = 4081c5d0dfbee34abf219b03a0d91b73f3688c45. PRECOMMIT_AUDIT·CLEAN_COMMIT_E2E·MC_PILOT으로 검증된 MC-V06 과학 구현이다.
  - APPROVED_EXECUTION_COMMIT = 이후 MC_FULL_RUN Gate Authorization이 정확한 SHA로 명시하는 merge 후 정본 commit이다. 단위 실행은 이 commit의 깨끗한 작업 트리에서 한다.
  - 과학 소스 파일(SCIENTIFIC_SOURCE_FILES) = manifest `source_sha256`에 기록되는 MC-V06 소스 6개: `src/moneylab/research/stats.py`, `src/moneylab/research/v06/__init__.py`, `src/moneylab/research/v06/montecarlo.py`, `src/moneylab/research/v06/procedures.py`, `src/moneylab/research/v06/risk_model.py`, `src/moneylab/research/v06/synthetic.py`.
  - APPROVED_EXECUTION_COMMIT가 Ce와 merge commit 때문에 CI_IMPLEMENTATION_COMMIT와 다른 것은 과학 구현 변경이 아니다. Ce는 `docs/tasks/MC-V06/ERRATA-001.md`만 바꾼다. merge는 과학 구현 변경을 들여오지 않아야 한다.
  - MC_FULL_RUN 전 확인: APPROVED_EXECUTION_COMMIT 트리의 SCIENTIFIC_SOURCE_FILES blob이 CI_IMPLEMENTATION_COMMIT 트리의 같은 파일 blob과 모두 같아야 한다. 하나라도 예상과 다르면 MC_FULL_RUN 전에 멈춘다.
  - 단위의 `execution.json` `git.commit`은 APPROVED_EXECUTION_COMMIT와 같아야 한다. merge 후에 이 값을 4081c5d로 고정하지 않는다.
  - 단위 `manifest.json`의 `source_sha256`(각 `git_blob_lf`)은 APPROVED_EXECUTION_COMMIT 트리와 대조한다. 그 트리의 SCIENTIFIC_SOURCE_FILES blob과 CI_IMPLEMENTATION_COMMIT의 동일성은 위 확인으로 따로 검증한다.
- MC_FULL_RUN_UNIT_CONTRACT (새 절):
  - 단위: MC_FULL_RUN은 정확히 18개의 시나리오 단위로 실행한다. 단위 목록과 순서는 APPROVED_EXECUTION_COMMIT의 `moneylab.research.v06.montecarlo.mc_v06_scenarios()`가 반환하는 목록 그대로다. CI_IMPLEMENTATION_COMMIT 기준 목록(순번_이름): 01 null_flat, 02 null_drift, 03 boundary_theta_0p3, 04 boundary_theta_0p5, 05 boundary_theta_0p7, 06 selection_stress, 07 garch_t_M60_-0p3, 08 normal_M60_-0p3, 09 garch_t_M60_+0p0, 10 normal_M60_+0p0, 11 garch_t_M60_+0p3, 12 normal_M60_+0p3, 13 garch_t_M60_+0p5, 14 normal_M60_+0p5, 15 garch_t_M60_+0p7, 16 normal_M60_+0p7, 17 garch_t_M60_+1p0, 18 normal_M60_+1p0. 실행 시점의 `mc_v06_scenarios()`가 이 목록(이름, 순서, `identity()`)과 다르면 실행하지 않고 멈춘다.
  - 호출: 각 단위는 `write_study(<unit_dir>, RunConfig(reps=R_OUTER, workers=<승인된 worker 수>), [scenario])` 한 번이다. RunConfig의 나머지 값(seed, truth_years, costs, procedure, layout, calendar)은 기본값(규범 값) 그대로이며 바꾸지 않는다. worker 수는 실행 운영 값일 뿐이고 18개 단위에 같은 값을 쓴다. worker 수는 난수 식별과 과학 결과에 영향을 주지 않는다. 보호 CLI `research-v06-sim`은 쓰지 않는다.
  - 출력 위치: MC_FULL_RUN Gate Authorization이 새 ignored 실행 루트 `<RUN_ROOT>`(실행 전 존재하지 않음)를 정한다. 단위 디렉터리는 `<RUN_ROOT>/<NN>_<scenario_name>_attempt<K>/`(NN = 위 순번, K = 1부터 시도 번호)이고 항상 새로 만든다. 기존 디렉터리를 덮어쓰거나 이어 쓰지 않는다.
  - 고정 순서: 단위는 위 순번대로 하나씩 차례로 실행한다(동시 실행 없음). 현재 시나리오에 정본 시도(아래)가 생기기 전에는 다음 시나리오로 넘어가지 않는다. 실패는 건너뛰기를 허용하지 않는다.
  - 시도와 실패: 단위 실행이 예외·중단·검증 실패로 끝나면 그 시도 디렉터리(임시 파일 포함)를 그대로 보존하고 지우거나 정리하지 않는다. 같은 시나리오를 다음 시도 번호의 새 디렉터리에 반복 0부터 다시 실행한다. 재실행은 이전 시도가 구조적으로 완료·검증되지 않았다는 이유로만 허용한다.
  - 정본 시도(canonical attempt): 시나리오마다 성공적으로 끝나고 아래 구조 검증을 통과한 첫 번째 시도다. 실패·불완전 시도는 정본이 될 수 없다. 정본 뒤에 같은 시나리오의 다른 완료 시도가 있으면 비정본으로 보존하고 MC_RESULT_AUDIT에서 과학 payload 동일성을 확인한다.
  - 구조 검증(실행 중 허용되는 유일한 확인): 다음만 확인한다.
    - 파일 존재: `manifest.json`, `execution.json`, `scenarios/<name>/summary.json`, `scenarios/<name>/records.jsonl`, `SHA256SUMS`.
    - `SHA256SUMS`가 나머지 모든 파일을 덮고 각 해시가 일치함.
    - `manifest.json`: schema = `moneylab.research_v06_sim/2`, evidence = `SYNTHETIC / NOT_EVIDENCE`, `normative_run = true`, `repetition_axes`의 R_OUTER·B_BOOT·K_RAND·TRUTH_YEARS가 모두 규범 값, `scenarios`가 정확히 한 항목이고 그 항목이 해당 순번 시나리오의 `identity()`와 같음.
    - provenance(PROVENANCE_TERMS): `execution.json`의 `git.commit` = APPROVED_EXECUTION_COMMIT, `manifest.json`의 `source_sha256` 각 `git_blob_lf` = APPROVED_EXECUTION_COMMIT 트리의 해당 파일 blob, 단위 실행 전 작업 트리가 깨끗함(tracked diff 0, staged 0, 예상 밖 untracked 0).
    - 반복 수: `records.jsonl`의 줄 수 = R_OUTER(값을 해석하지 않고 줄만 센다).
    - `summary.json`은 존재만 확인한다. 이 단계에서 summary·records의 과학 값을 열거나 해석하지 않는다.
  - 결과 미열람·비적응: 18개 시나리오 모두에 정본 시도가 생기기 전에는 `summary.json`과 `records.jsonl`의 과학 결과 값을 열람·비교·요약·해석하지 않는다. 중간 시나리오 결과로 파라미터, 실행 순서, 시나리오 포함 여부, 성공한 시나리오의 반복, 조기 중단, 이후 실행을 바꾸지 않는다.
  - checkpoint/resume 아님: 이 시나리오 단위 실행은 반복 수준 checkpoint/resume이 아니다. 어떤 단위도 일부 반복 집합에서 이어 실행하지 않는다. 실패한 단위는 그 시나리오 전체를 반복 0부터 새 디렉터리에서 다시 실행한다. 구현 수준의 resume/checkpoint 기능을 추가하지 않는다.
  - 난수·과학 동등성 근거: 위 RATIONALE의 확인대로, 시나리오 과학 payload(`scenarios/<name>/summary.json`, `scenarios/<name>/records.jsonl`)는 같은 과학 구현(SCIENTIFIC_SOURCE_FILES blob), 같은 규범 설정, 같은 Python·실행 환경 가정, 같은 seed에서 단일 호출의 해당 시나리오 payload와 바이트가 같다고 기대된다. 단위의 `manifest.json`은 `scenarios` 항목과 실행 메타데이터 성격의 필드에서, `execution.json`은 실행 메타데이터(시각, worker, 실행 Git 식별, 플랫폼)에서 단일 호출과 정당하게 다를 수 있다. 이 둘의 전체 동일성은 주장하지 않는다.
- NO_RESUME_FEATURE: 기존 두 문장은 그대로 둔다. 다음 해석을 더한다: MC_FULL_RUN_UNIT_CONTRACT의 시나리오 단위 실행과 실패 단위의 새 디렉터리 전체 재실행은 checkpoint/resume 기능이 아니며, 이 절이 금지하는 범위 확장이 아니다. 반복 수준의 이어 실행은 계속 금지다.
- ALLOWED_ACTIONS.MC_FULL_RUN: "Gate Authorization이 정한 규범 전체 실행, 새 ignored 출력 경로에만"을 다음으로 읽는다: MC_FULL_RUN_UNIT_CONTRACT에 따른 18개 시나리오 단위의 순차 실행. Gate Authorization은 최소한 APPROVED_EXECUTION_COMMIT(정확한 SHA), `<RUN_ROOT>`, worker 수를 정한다. 단위 호출 형태, 순서, 디렉터리 규칙, 재실행 규칙은 이 ERRATA가 정하며 Gate Authorization이 바꾸지 못한다.
- ARTIFACT_PROVENANCE_CONTRACT: "전체 실행 산출물"은 다음 전체로 정의한다: (1) 18개 정본 단위 산출물 집합(각각 자체 `manifest.json`, `execution.json`, `scenarios/<name>/summary.json`, `scenarios/<name>/records.jsonl`, `SHA256SUMS`), (2) 보존된 실패·비정본 시도, (3) MC_RESULT_AUDIT의 완전성·무결성 판정. 단위별 `SHA256SUMS`가 계약의 무결성 기록이다. 단일 manifest나 단일 `SHA256SUMS`를 사후에 만들어 내지 않는다(별도 계약 승인 없이). 스키마 `/2`와 구현 코드는 바뀌지 않는다.
- PROCEDURE_ACCEPTANCE.MC_FULL_RUN: 각 항목은 18개 정본 단위의 집합에 적용한다. "미리 정한 규범 시나리오 격자 완료" = 18개 시나리오 모두에 정본 시도가 있음. 반복 수·적응적 중단 없음·실행 중 파라미터 변경 없음·MC SE·provenance·무결성 해시·SYNTHETIC / NOT_EVIDENCE 표시는 정본 단위마다 성립해야 한다.
- PROCEDURE_ACCEPTANCE.MC_RESULT_AUDIT: 과학 결과를 열기 전에 읽기 전용 구조 집계 감사를 먼저 한다. 최소 확인 항목:
  1. 18개 `mc_v06_scenarios()` 식별마다 정본 완료 단위가 정확히 하나 있다.
  2. 정본 식별들의 집합이 기대하는 18개 시나리오 집합과 정확히 같다.
  3. 정본 단위 순번이 `mc_v06_scenarios()` 순서와 대응한다.
  4. 모든 정본 `SHA256SUMS`가 검증된다.
  5. provenance(PROVENANCE_TERMS): 모든 정본 단위의 `execution.json` `git.commit`이 같은 APPROVED_EXECUTION_COMMIT이다. 모든 정본 단위의 `source_sha256`이 서로 같고 APPROVED_EXECUTION_COMMIT 트리와 일치한다. 그 트리의 SCIENTIFIC_SOURCE_FILES blob이 CI_IMPLEMENTATION_COMMIT의 해당 blob과 같다.
  6. 동결된 규범 설정과 실행 환경 식별: 다음 필드는 18개 정본 단위에서 값이 서로 같고 규범 값과 같아야 한다 — `manifest.json`의 `schema`, `evidence`, `normative_run`(= true), `repetition_axes`(R_OUTER, B_BOOT, K_RAND, TRUTH_YEARS), `seeds`(seed와 파생 seed 규칙), `procedure`, `layout`, `simulation_calendar`, `costs`, `decision_grid`, `target_max_mc_se`, `adaptive_stopping`, `source_sha256`, `python`, `python_implementation`. `execution.json`의 `python`, `platform`, `workers`(승인된 worker 수)도 18개 단위에서 같아야 한다. 각 단위의 `scenarios[0]`은 해당 순번의 기대 시나리오 `identity()`와 같아야 한다. 이 필드 목록 밖의 manifest 필드에 대해 일괄적인 바이트 동일성은 요구하지 않는다. 운영·비과학 메타데이터의 차이는 그것만으로 과학 동등성을 무효로 하지 않는다. 단, 이 항목이나 다른 항목이 같음을 요구한 필드가 다르면 실패다.
  7. 정본 단위마다 records가 정확히 R_OUTER개이고 summary의 `records` 기록(개수, SHA-256)이 `records.jsonl`과 일치한다.
  8. 각 manifest의 시나리오 식별이 기대 시나리오와 같다.
  9. schema = `moneylab.research_v06_sim/2`.
  10. `normative_run = true`.
  11. 실패·비정본 시도가 모두 목록에 있고 보존되어 있다(삭제 흔적 없음, 시도 번호 연속).
  12. 한 시나리오에 완료 시도가 둘 이상 있으면 과학 payload(`summary.json`, `records.jsonl`) 바이트 동일성을 확인한다.
  구조 집계 감사가 통과한 뒤에만 과학 결과를 열고 해석한다. 실패하면 멈추고 과학 해석을 하지 않는다. 그 밖의 기존 MC_RESULT_AUDIT 항목은 그대로다.
- STOP_CONDITIONS: 다음을 더한다. 멈추고 사용자 결정을 요청한다.
  - 같은 시나리오의 완료 재실행이 설명되지 않는 과학 payload 차이를 만듦.
  - 난수 식별 가정과 모순되는 사실이 드러남.
  - 동결된 규범 설정에서 단위를 완료할 수 없음.
  - 실행에 과학 파라미터 변경이 필요함.
  - 실행에 구현 수준 checkpoint/resume이 필요함.
  - 기대 시나리오를 구조적으로 검증할 수 없음.
  - 실행 commit이 APPROVED_EXECUTION_COMMIT와 다르거나, APPROVED_EXECUTION_COMMIT의 SCIENTIFIC_SOURCE_FILES blob 중 하나라도 CI_IMPLEMENTATION_COMMIT과 예상과 다르게 다름(MC_FULL_RUN 전에 멈춤).
  - 어떤 규범 파라미터든 다름.
  - 실행 시점의 `mc_v06_scenarios()`가 위 18개 목록과 다름.
  범위를 자동으로 넓히지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 이 ERRATA는 MC_FULL_RUN의 실행 조직(orchestration)과 실패 영역 크기만 명확히 한다. R_OUTER, B_BOOT, K_RAND, TRUTH_YEARS, TARGET_MAX_MC_SE, ADAPTIVE_STOPPING, 시나리오 정의·개수·순서, seed와 난수 파생, 과학 절차, 판정 규칙, 위험 의미, 달력 의미, 스키마 `/2`, 구현 코드, 통계 해석을 바꾸지 않는다.
- 구현 코드 변경 없음. ALLOWED_FILES와 PROTECTED_FILES 변경 없음. CI_IMPLEMENTATION_COMMIT(4081c5d)을 대체하지 않는다.
- 이 파일은 ACCEPTED ERRATA gate의 Ce 커밋(`docs(task): add MC-V06 ERRATA-001`)에서 승인된 문구 그대로 한 번만 만든다. Ce는 이 파일만 바꾼다. amend·이력 재작성 없음. 기대 branch 이력: C1 → Ci → Ce. PR은 Create a merge commit으로 합치고, merge는 과학 구현 변경을 들여오지 않는다.
- MC_PILOT 결과는 이 ERRATA의 어떤 값도 정하지 않았다. pilot은 실패 영역의 크기만 보여 주었다.
- BT-4 결정(D1–D9, 위험 정책 값, BT4-Q18)은 계속 DEFERRED_TO_BT4다.
