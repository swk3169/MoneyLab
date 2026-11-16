AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS

# AUTO-07 고정 파일 전달 검증 사례 기록

이 기록은 비권위 관측 기록이다. 실행 사실, 출처, 작성자, 승인, gate PASS, 무인 운영 준비, 실제 실행 바이트의 독립 인증, 안전성을 증명하지 않는다.

- 초안 작성일: 2026-11-16
- 경로의 날짜(2026-11-16)는 사례 식별용이다.
- probe 실제 실행 시각: 미관측. 도구가 시각을 보고하지 않았고, 추정하지 않는다.

## 1. 요약 (이 기록의 초안 확정 시점 기준)

- D7 판정: UNKNOWN. 확인된 불일치는 없다. 출력 끝 LF 개수 1항목이 미확정이다.
- probe 실행: 누적 1회(상한 1회). 도구가 보고한 실제 종료 코드는 7이다.
- task 종료 상태: 계약·지시 위반 1건(DEVIATION #1)이 기록되었다. 따라서 COMPLETION 규칙에 따라 COMPLETE는 불가하며, CLOSED_WITH_VIOLATION 대상이다. D7 판정과 task 종료 상태는 별개다.

## 2. 기준과 커밋 (등급 GIT_VERIFIABLE)

| 항목 | SHA | tree | parent |
|---|---|---|---|
| CANONICAL_BASE | `2a05e0bbdc7a050514860128007ca48b8427121e` | `ab52b586b69e474242dd5a8db585a2bf94afcd96` | - |
| C1 (Work Order) | `1f3bed24d8b9924a8f453617d417c59ca75aac55` | `322223083b95ce559e556a99f9892894551a3510` | CANONICAL_BASE |
| I1 (probe, 테스트) | `50ec4d920fc739f9ebadc0e99eca1ed33b8f5045` | `2bab4e5627a8dfd242612c01a6600e9ada6a797a` | C1 |

- `docs/tasks/AUTO-07/WORK_ORDER.md` sha256: `9ffc5f455999b4677a7abcf8c21ddf8a6d31efdc6b84ecf68e2272899cd06a7d`
- `tools/auto07_delivery_probe.py`: 원바이트 W = I1 blob S = 내용 해시 = `c56693d156fa09a1cf9334574e4454b1bee33f4e3977ee17e46569d639181622`, 58바이트, LF 4. 원바이트에 CR이 없으므로 내용 해시와 같다.
- `tests/test_auto07_delivery_probe.py`: W = S = `98448f386e1bb4cc290c23f5276fb44ea250cbed170e79b57d75df7da9c03d20`, 2173바이트, LF 52

## 3. 작업공간과 환경 (ENVIRONMENT_PREPARATION_ONLY 시점 관측, 이후 재확인하지 않음)

- 작업공간은 SOURCE_WORKTREE, TARGET_WORKTREE, BASE_PYTHON으로만 표기한다.
- D1 확인값(등급 CLAUDE_REPORTED):
  - Python 3.14.8
  - sys.prefix가 TARGET_WORKTREE의 .venv
  - moneylab.__file__이 TARGET_WORKTREE의 src 아래
  - 고정 의존성 24개의 이름·버전 일치. 허용 집합 밖 배포판 0개
  - pip check 통과
  - mypy 2.4.0 (compiled: no)
- 준비 직후 ignored 항목: `.venv/`, `src/moneylab.egg-info/` (등급 GIT_VERIFIABLE)
- 관측 한계: 격리 빌드 의존성의 실제 목록과 임시 빌드 산출물의 삭제 여부는 확인하지 않았다.

## 4. 로컬 검사 (D5, 등급 CLAUDE_REPORTED)

- I1 PRECOMMIT_AUDIT, skip 근거 재진입, I1 CLEAN_COMMIT_E2E에서 각각 pytest를 실행했다. 세 번 모두 58 passed, 3 skipped, 실패·오류 0이었다. probe 테스트는 2개 모두 통과했고 skip은 0이었다.
- ruff는 두 번 실행했고 두 번 모두 통과했다.
- hygiene skip 3건의 출력 사유는 모두 "no local research runs (data/ is git-ignored)"였다. 소스 위치를 대응시키면 다음 세 테스트다.
  - `test_run_manifests_match_current_study_files`
  - `test_locked_test_splits_match_manifest_and_stay_unopened`
  - `test_raw_datasets_match_recorded_raw_manifest`
- 각 검사 전후 git status(ignored 포함)는 같았다.

## 5. 실행 관측 (D6)

- 실행 전 확인(관측 시점: 실행 직전): branch, HEAD = I1, tree = I1 tree가 일치했다. tracked·index·untracked 변경은 없었고 ignored는 2개뿐이었다. probe W = S = 승인값이었고, Work Order W = C1 blob이었다.
- 실제 호출: `cd <TARGET_WORKTREE> && ./.venv/Scripts/python.exe -B tools/auto07_delivery_probe.py` 1회. 승인 명령 앞에 `cd`와 `&&`가 붙었다(7절 DEVIATION #1).
- 도구가 표시한 내용:
  - 도구 메타데이터: 종료 코드가 0이 아니어서 error 형식으로 표시되었고, `Exit code 7`이 함께 표시되었다.
  - 프로그램 출력으로 표시된 문자열: `AUTO07_DELIVERY_PROBE_OK` 한 줄. 다른 줄은 없었다.
- 실제 종료 코드: 7 (도구 보고값)
- Guard 차단과 권한 요청은 관측되지 않았다. 이것은 승인 증거가 아니다. 실행 전 별도 대화 승인이 있었고 해시·상태 대조를 수행했다. 도구의 추가 권한 요청은 관측되지 않았다.
- 실행 후 확인(관측 시점: 실행 직후): branch·HEAD·tree, probe W·S, Work Order W·C1 blob, tracked·index·untracked 상태, ignored 2개가 실행 전과 같았다. `tools/__pycache__`는 0개였다.

## 6. D7 판정과 근거

- 판정: UNKNOWN. 이 판정은 ERRATA로 소급 변경하지 않는다.
- NOT_RUN이 아닌 근거: 도구가 종료 코드와 출력을 보고했으므로 프로세스는 시작된 것으로 본다.
- FAIL이 아닌 근거: 확인된 불일치가 없다. 출력 문자열은 기대값과 같고, 종료 코드는 7이며, 실행 후 해시와 상태가 진입 조건과 같다.
- UNKNOWN 항목: 출력 끝 LF가 1개인지는 도구 표시로 확인하지 못했다.
- 추론(관측 아님): 소스상 print의 기본 끝 문자는 LF 1개다. 이 추론은 판정 근거로 쓰지 않는다.

## 7. 이벤트와 이탈 (AUTO-07 기준, 이 기록의 초안 확정 시점까지)

- 이벤트 1건: 첫 EXECUTION_ONLY 승인문이 손상되어 실행 전에 중단했다. 예상된 중단이며 위반이 아니다. 그 승인으로 probe를 실행한 횟수는 0회다.
- DEVIATION #1 (계약·지시 위반):
  - 실행 승인문은 "명령에 다른 명령이나 리디렉션을 붙이지 않는다"고 정했다. 그러나 실제 호출에는 `cd <TARGET_WORKTREE> &&`가 추가되었다.
  - 설명: 작업 디렉터리를 TARGET_WORKTREE로 설정하려는 목적이었다.
  - 관측된 영향: 출력에 cd로 인한 추가 내용은 없었다. 실행 전후 상태 대조에서 차이도 관측되지 않았다.
  - 위 목적과 관측된 영향은 위반을 없애지 않는다.
- task 종료 상태: COMPLETION 규칙상 위반이 1건 이상이므로 COMPLETE는 불가하다. task는 CLOSED_WITH_VIOLATION 대상이다. 이후 승인, ERRATA, 정정으로 이 위반을 없애지 않는다.

## 8. 관측 한계

- stdout과 stderr를 분리하지 않았다. 표시된 문자열이 어느 스트림에서 나왔는지는 확인하지 않았다.
- 출력 끝 LF 개수는 미확인이다.
- 실행 전후 해시가 일치한 것은 각 관측 시점의 사실이다. 실행 중 파일이 바뀌지 않았다는 것이나, 인터프리터가 실제로 읽은 바이트를 독립적으로 인증하지 않는다.
- 해시 고정과 AST 구조 검사는 승인 바이트와의 동일성과 검토된 구성을 기록한다. 실행 시 안전을 보장하지 않는다.
- 다른 checkout의 원바이트 동일성은 보장하지 않는다. 그런 경우에는 내용 해시만 의미가 있다.
- probe 실행 시각은 미관측이다.
