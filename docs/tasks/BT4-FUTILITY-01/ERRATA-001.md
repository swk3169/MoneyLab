# ERRATA: BT4-FUTILITY-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-01-ERRATA-001
TASK_ID: BT4-FUTILITY-01
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-01/WORK_ORDER.md @ 7ac09a674e68cbc95dd5c934f2d3580939fd02f0 (sha256 c1e7003788d3878c8812b8bd1dd93b5d1df28d21c01b84099225a99525bf3b8b)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## ISSUE

ISSUE: TEST_GATES 첫 항목(WORK_ORDER.md:358)은 "새 venv나 junction을 만들지 않는다"고 정한다. 저장소 guard hook(.claude/settings.json:52, 우선순위 2)은 `${CLAUDE_PROJECT_DIR}/.venv/Scripts/python.exe`로 .claude/hooks/guard.py를 실행하고, 실행에 실패하면 fail-closed(exit 2)로 호출을 막는다. TARGET_WORKTREE에 .venv가 없어서 guard 실행이 실패했다. 사용자는 2026-10-29에 `py -3.14 -m venv .venv`로 C:/MoneyLab-bt4-futility-diag/.venv(Python 3.14.8)를 만들었고, 이후 guard는 정상 판정한다. 이 .venv는 .gitignore:24로 무시된다. 우선순위 2(guard 실행 요건)와 4(TEST_GATES)의 문구가 충돌하므로 계약을 맞춘다.

## CHANGED_FIELDS

CHANGED_FIELDS:
- TEST_GATES 첫 항목: "새 venv나 junction을 만들지 않는다"에 GUARD_RUNTIME_VENV_EXCEPTION 1개 추가(기존 문장 유지)

UNCHANGED_FIELDS (명시적으로 바꾸지 않음): 테스트·E2E·pilot·MC 인터프리터 `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe`, `PYTHONPATH=C:/MoneyLab-bt4-futility-diag/src`(A9), `moneylab.__file__` 위치 확인, junction·symlink 금지, FORBIDDEN_ACTIONS(패키지 설치·의존성 추가 금지, hooks·settings·.claude 변경과 guard 우회 금지 포함), POLICY_VALUES, 사전등록(sha256 6da9e20088b1a6ca5c9ce9696c0baadd0850d7aa409f962f2583b188b322189f)과 config(sha256 3df664508e117ae25b05d7de49b3f62dec1c6ef55eab185ce0cf52f631351723), DC1–DC14와 DC4.1, seed 이름공간과 MC-V06 seed 규칙, TEST_GATES의 나머지 항목, E2E_GATES, GATE_SEQUENCE, GATE_TABLE, ALLOWED_FILES, PROTECTED_FILES, .claude/hooks/guard.py, .claude/settings.json.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- GUARD_RUNTIME_VENV_EXCEPTION (TEST_GATES 첫 항목에 추가):
  - `C:/MoneyLab-bt4-futility-diag/.venv`(사용자 생성, ignored)는 guard hook 인터프리터로만 쓴다. 이 용도 제한은 venv에 설치된 패키지와 관계없이 적용된다.
  - 이 venv로 테스트, E2E, pilot, MC, 분석, `moneylab` 명령을 실행하지 않는다.
  - 이 venv에 패키지를 설치·제거·업그레이드하지 않는다(`pip install -e .` 포함). venv를 다시 만들거나 교체하지 않는다. 사라지거나 손상되면 STOP하고 사용자에게 보고한다.
  - 테스트·E2E·pilot·MC 인터프리터는 `C:/MoneyLab-mc-v06/.venv/Scripts/python.exe` + `PYTHONPATH=C:/MoneyLab-bt4-futility-diag/src`로 유지한다.
  - junction·symlink는 예외에 포함되지 않는다.
  - 이 예외는 위 venv 하나를 사후 승인할 뿐이다. Claude에게 venv 생성, 테스트 인터프리터 변경, guard·hook·settings 변경 권한을 주지 않는다.

## RATIONALE

RATIONALE: guard는 우선순위 2이고 Work Order가 바꿀 수 없다. guard를 바꾸거나 우회하지 않고 실행 요건만 맞추는 최소 변경이다. 테스트 인터프리터를 바꾸지 않으므로 의존성 집합, Python 빌드, 수치 결과의 재현 조건은 바뀌지 않는다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- .venv/는 ignored이므로 tracked 파일, HEAD, 소스·테스트·Work Order·사전등록·config SHA256, MC-V06 `_SOURCE_FILES`에 영향이 없다.
- Ce 커밋은 이 파일 하나만 추가한다. HEAD가 Ce로 바뀌는 것 외에 tracked 변경은 없다.
- 이미 수행된 G3 단계(G3a/G3b 등)의 결과가 이 ERRATA 이전에 유효했는지는 이 ERRATA가 정하지 않는다. docs/tasks/README.md §6("변경 gate가 의존하는 ERRATA는 먼저 Ce로 고정한다")에 따라 사용자가 판단한다.

## SECURITY_IMPACT

SECURITY_IMPACT:
- guard 정책, 코드, 설정은 바뀌지 않는다. fail-closed guard가 다시 판정할 수 있게 된다.
- BT4 .venv의 설치 패키지 구성은 이 ERRATA에서 확인하지 않았다(미검증). 용도 제한은 패키지 구성과 관계없이 적용된다.
- guard ROOT:
  - CONFIRMED: guard.py:32 `ROOT = Path(__file__).resolve().parents[2]`. settings.json:52가 `${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.py`를 실행한다.
  - INFERRED: hook 실행 시 CLAUDE_PROJECT_DIR = C:/MoneyLab-bt4-futility-diag. 근거는 BT4 .venv가 없을 때 hook이 실패했고 만든 뒤 해소된 것이다(C:/MoneyLab에는 .venv가 있다). 값을 직접 관측하지는 못했다(Bash 도구 환경에서는 빈 값).
- 남는 위험: hook 인터프리터가 ignored 경로에 있어서 교체를 git이 잡지 못한다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA (G3 변경 gate 전에 읽기 전용으로 확인):
- AC-1: C:/MoneyLab-bt4-futility-diag/.venv/Scripts/python.exe가 있고 Python 3.14.x이며 `git check-ignore`로 ignored다.
- AC-2: tracked·staged 변경 0, .venv 아래 tracked 파일 없음.
- AC-3: C:/MoneyLab-mc-v06/.venv/Scripts/python.exe가 있다. G3에서 PYTHONPATH 적용 시 `moneylab.__file__`이 TARGET_WORKTREE 아래인지 확인한다.
- AC-4: 정상적인 읽기 전용 호출에서 guard가 오류 없이 판정한다.
- AC-5: Ce 커밋 전후 이 파일의 sha256이 같고 커밋 파일이 이 파일 하나다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- ACCEPTED 이후 이 파일은 불변이다. 철회·수정은 ERRATA-002로만 한다.
- Claude는 BT4 .venv를 삭제·교체하지 않는다(FORBIDDEN_ACTIONS: ignored 파일 정리 금지). 사용자가 결정한다.
- venv가 사라지거나 손상되면 guard가 fail-closed로 막는다. STOP하고 보고한다.

## APPROVAL

APPROVAL:
- 사용자가 이 문서의 최종 문구를 수락했다(ACCEPTED). 이 ERRATA는 Ce 커밋으로 고정되며 계약(우선순위 4)을 바꾼다.
- ACCEPTED 문구 확정과 Ce 커밋(파일 생성, 경로를 지정한 stage, 커밋, sha256 보고)은 각각 사용자의 별도 승인으로 수행한다.
- Ce 전에는 G3 구현을 시작하지 않는다.
