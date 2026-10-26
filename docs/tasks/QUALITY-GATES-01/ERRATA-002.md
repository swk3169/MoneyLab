# ERRATA-002: QUALITY-GATES-01 — F811 억제 위치 정정

이 파일은 불변이다. 발행(Ce2) 후 수정하지 않는다.

## Metadata

ERRATA_ID: QUALITY-GATES-01/ERRATA-002
TASK_ID: QUALITY-GATES-01
STATUS: ACCEPTED
ACCEPTED_IN_GATE: ERRATA-002_SCOPE_DECISION (사용자 Gate Authorization)
APPLIES_TO_WORK_ORDER: docs/tasks/QUALITY-GATES-01/WORK_ORDER.md @ C1v2 `5f7bb60bc1d1ac547fc94f25c6c2fcde09d2caa9` (sha256 5581c56a91b5fd0e98e8564a7713516906a5916d4da7c35a0d7079273d4a9f5a)
AMENDS: docs/tasks/QUALITY-GATES-01/ERRATA-001.md @ Ce1 `d5e16f0e09f108cc653b3c508f94246c15cee98d` (sha256 557a8fba05c98cc576b6a710da06997854620cf24bd9dd6c1b14926f9b1270bb)
SUPERSEDES: ERRATA-001의 F811 수정 방식(ALLOWED_FILES_ADDITIONS 표의 6·7행 "허용 수정" 열, RUFF_REMEDIATION_RULES의 "`noqa` 추가는 F811이 필요한 fixture import 줄에만 한다. 다른 줄에 `noqa`를 넣지 않는다")만. 그 밖의 Work Order와 ERRATA-001 조항은 모두 유지한다.

## FINDING

FINDING (CLAUDE_REPORTED, IMPLEMENTATION gate, ruff 0.17.2):
- ERRATA-001대로 `tests/test_backtest_code_state.py`와 `tests/test_backtest_report.py`의 fixture import 줄을 `# noqa: F401, F811`로 바꾼 뒤에도 `ruff check --no-cache --select E4,E7,E9,F src tests`가 F811 12건을 보고했다(exit 1). F401은 0건이 되었다.
- ruff는 F811을 import 줄이 아니라, import한 pytest fixture 이름 `bars`가 fixture 인자로 다시 정의되는 함수 정의 위치에 보고한다. 그래서 import 줄의 `noqa`는 이 진단에 적용되지 않는다.
- 남은 F811 위치(IMPLEMENTATION 측정 당시 줄 번호):
  - `tests/test_backtest_code_state.py`: 78, 92, 105, 111, 117, 129
  - `tests/test_backtest_report.py`: 35, 101, 121, 133, 224, 305

## CORRECTED_F811_REMEDIATION

대상 파일은 ERRATA-001이 이미 허용한 두 경로뿐이다(새 경로 없음):
- `tests/test_backtest_code_state.py`
- `tests/test_backtest_report.py`

수정 방식:
1. fixture import 줄의 지시문을 원래 형태 `# noqa: F401  (bars is a fixture)`로 되돌린다. 기존 설명 주석은 그대로 둔다.
2. 검증된 F811 진단마다, 그 진단이 붙은 함수 정의 문장 하나에 `# noqa: F811`을 붙인다. 진단 하나에 억제 하나다.

| 파일 | 진단 위치(측정 당시 줄) | 함수 정의 |
|---|---|---|
| `tests/test_backtest_code_state.py` | 78 | `def test_review_documents_only_do_not_fail_verification(tmp_path, bars):` |
| `tests/test_backtest_code_state.py` | 92 | `def test_untracked_execution_files_fail_now_and_at_run_time(tmp_path, bars, extra):` |
| `tests/test_backtest_code_state.py` | 105 | `def test_tracked_changes_fail(tmp_path, bars, xy):` |
| `tests/test_backtest_code_state.py` | 111 | `def test_commit_change_fails(tmp_path, bars):` |
| `tests/test_backtest_code_state.py` | 117 | `def test_settings_change_fails_in_settings_and_code(tmp_path, bars):` |
| `tests/test_backtest_code_state.py` | 129 | `def test_clean_run_reverifies_without_writing(tmp_path, bars):` |
| `tests/test_backtest_report.py` | 35 | `def run(bars, tmp_path_factory):` (module fixture) |
| `tests/test_backtest_report.py` | 101 | `def test_no_trades_report(tmp_path, bars):` |
| `tests/test_backtest_report.py` | 121 | `def test_fee_zero_vs_positive(tmp_path, bars):` |
| `tests/test_backtest_report.py` | 133 | `def test_not_aligned_run_has_no_comparison(tmp_path, bars):` |
| `tests/test_backtest_report.py` | 224 | `def test_check_report_detects_run_tampering(tmp_path, bars):` |
| `tests/test_backtest_report.py` | 305 | `def test_v2_sections_without_trades_and_when_not_aligned(tmp_path, bars):` |

- 위치는 줄 번호가 아니라 ruff가 실제로 진단을 보고한 함수 정의로 식별한다. 편집으로 줄 번호가 바뀔 수 있다.
- Python 문법상 다른 위치가 필요하다고 ruff가 보이는 경우가 아니면, 억제는 진단당 정확히 하나다.

PREFLIGHT_EVIDENCE (CLAUDE_REPORTED, ERRATA-002_SCOPE_DECISION, 파일 변경 없음):
- 현재 작업 파일 내용에서 CR을 제거하고 위 12개 함수 정의 줄에 `  # noqa: F811`을 붙인 결과를 `ruff check --no-cache --select E4,E7,E9,F --stdin-filename <path> -`로 넘겼다: 두 파일 모두 `All checks passed!`, exit 0.
- 대조군(같은 입력, 함수 정의 줄 noqa 없음): 파일마다 `Found 6 errors.`
- 이 확인은 stdin pipe만 썼고 저장소 파일은 바꾸지 않았다(미commit diff 지문 전후 동일).

FORBIDDEN (F811 정정):
- 파일 단위 ignore, 전역 F811 ignore, `per-file-ignores` 설정
- 다른 ruff 규칙 억제
- fixture 이름이나 함수 인자 변경, fixture를 `conftest.py`로 옮기기, test 구조 refactor, test 동작 변경
- 관련 없는 줄 수정, `ruff --fix`
- 이 함수 정의 줄 noqa 방식이 ruff 0.17.2에서 F811을 억제하지 못하면 멈춘다. 새 사용자 결정 없이 다른 억제 방식을 시도하지 않는다.

## IMPLEMENTATION_RESUME

- 다음 gate: IMPLEMENTATION_RESUME. 이 gate는 IMPLEMENTATION의 연속이며 ALLOWED_FILES(IMPLEMENTATION)와 ERRATA-001의 7개 경로 범위 안에서만 동작한다.
- 할 일: 두 fixture import 줄을 F401 전용 지시문으로 되돌림, 12개 F811 억제 추가, ruff 재실행, ruff 통과 시 생략했던 pytest·coverage 검증 실행, 이미 만든 `pyproject.toml`·`requirements-dev.txt`·Windows CI·Linux 실험 job 변경 감사, 원래 IMPLEMENTATION 검증 완료.
- ERRATA-002_SCOPE_DECISION gate에서 이미 만든 미commit 구현 변경 10개 경로는 바꾸지 않고 보존한다.

## PRESERVED

이 ERRATA가 명시적으로 대체한 F811 수정 방식 외의 C1v2와 ERRATA-001 제약(7개 경로 한정, wildcard 거부, mypy 범위와 호출, types-requests 제외, coverage·format 관찰 전용, SUPERSEDED lineage 보호, Q0 결과)은 그대로 유지한다. 이 ERRATA에는 machine-local 사용자 홈 경로나 Windows 계정명을 쓰지 않는다.
