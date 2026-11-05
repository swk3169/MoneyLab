# ERRATA: BT4-FUTILITY-02 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: BT4-FUTILITY-02-ERRATA-001
TASK_ID: BT4-FUTILITY-02
TARGET_WORK_ORDER: docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md
TARGET_WORK_ORDER_COMMIT: 29e8e446a9a36ee2bad2aa674339f414c09bb24d
TARGET_WORK_ORDER_SHA256: cb5a0efe24137ec45b34cb8c21680c12a54662e5d0a9fef2505358b42b360bf7
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: USER

## ISSUE

ISSUE:
- G2 전체 pytest(T1)가 실패했다.
  - PYTHONPATH 없이: 32 failed.
  - PYTHONPATH=C:/MoneyLab-bt4-futility-02/src: 2 failed.
- 원인 1: tests/test_agent_guard.py의 wrapper 테스트 2건은
  .claude/settings.json:52의 hook 명령을 TARGET_WORKTREE 기준
  `${CLAUDE_PROJECT_DIR}/.venv/Scripts/python.exe`로 실행한다.
  - 대상: test_wrapper_passes_real_decisions_through,
    test_wrapper_cannot_fix_invalid_json_with_exit_0
  - TARGET_WORKTREE에 .venv가 없다.
- 원인 2: 사용한 인터프리터 C:/MoneyLab-mc-v06/.venv의 editable 설치
  (__editable__.moneylab-0.3.0.pth)가 C:\MoneyLab\src를 가리킨다.
  - `sys.executable`로 실행되는 subprocess 테스트가
    TARGET_WORKTREE/src가 아닌 코드를 import했다.
  - pytest의 pythonpath 설정(pyproject.toml:30)은 subprocess에 전달되지 않는다.
- 같은 원인으로 G3c(T1 재실행)와 G5·G6 D10 단계 0
  (모듈 파일이 TARGET_WORKTREE/src 아래)을 충족할 수 없다.
- WORK_ORDER.md:134·:316은 venv 생성, 패키지 설치,
  환경 변수 소스 경로 주입을 금지한다. 따라서 계약을 바꾼다.

## CHANGED_FIELDS

CHANGED_FIELDS:
- FORBIDDEN_ACTIONS(:134)와 D10(:316): TASK_TEST_VENV_EXCEPTION 1개를 추가한다.
  기존 문장은 유지하며 예외 밖은 계속 금지한다.
- ALLOWED_FILES(:144-147): 다음 1행을 추가한다.
  `A docs/tasks/BT4-FUTILITY-02/ERRATA-001.md (Ce 전용)`
- PROTECTED_FILES(:153): docs/tasks/BT4-FUTILITY-02/**의 예외에
  "Ce의 ERRATA-001.md 최초 생성"을 추가한다.
- INVARIANT(:161): 예외에 같은 파일 하나를 더한다.
- PR_SCOPE(:149), GATE_TABLE G4b PASS(:388), STOP_CONDITIONS(:446):
  "3경로"를 아래 "4경로"로 바꾼다.
  - docs/tasks/BT4-FUTILITY-02/WORK_ORDER.md
  - docs/tasks/BT4-FUTILITY-02/ERRATA-001.md
  - src/moneylab/research/v06/futility_02.py
  - tests/test_v06_futility_02.py
- D1 changed-path(:242): `d2fcaf6..HEAD` 변경 경로의 허용 집합을 위 4경로로 바꾼다.
- D10 단계 0(:308)과 PYTHON_VERSION(:34): 실행 파일을 TASK_PYTHON으로 고정한다.
- G2 진입 조건(:383): G2 계속 조건을 추가한다(REPLACEMENT_CONTRACT).
- G3b(:385): C2의 parent = Ce를 추가한다.
- 승인 식별자(:59): G2 재검증 이후 ERRATA 커밋을 함께 적는다.
- GATE_SEQUENCE(:46): G2 진행 중에 E1·E2·E3을 삽입하고, 그 뒤 G2 재검증을 한다.

## UNCHANGED_FIELDS

UNCHANGED_FIELDS (명시적으로 바꾸지 않음. CHANGED_FIELDS에 적은 부분 외 전부):
- WORK_ORDER.md 파일 자체(내용·sha256)
- Metadata의 나머지 값(ACCEPTED_ERRATA 줄 포함, 원본은 수정하지 않는다)
- GOAL, BACKGROUND, SCOPE
- D0, D2~D9, D11~D13의 정의·식·계산 순서·failure_code·출력 스키마
- D1의 changed-path 외 항목(Python 3.14.8·win32, realpath 비교, HEAD, 모듈 위치,
  clean, branch, 코드 7행 blob·LF 비교, d2fcaf6 조상 조건, NEW_OUTPUT_ROOT ignored)
- D10의 실행 파일 고정 외 항목(시도 디렉터리, mkdir, stderr.bin, 계산 순서, exit code)
- INPUT_HASH_MANIFEST 35행
- PROVENANCE_ACCESS_POLICY
- TEST_GATES T1~T11의 내용(T1 옵션 `-p no:cacheprovider -rfEs -q` 포함)
- E2E_GATES
- REQUIRED_CI_CHECKS, OPTIONAL_CI_CHECKS, EXPECTED_REMOTE_MAIN
- PR_STRATEGY OPTION_B, PR_TYPE DRAFT, PR_POLICY DO_NOT_MERGE, MERGE_METHOD
- D13 E1~E5
- 결과 비공개(PUBLIC_RESULT_REPORT NOT_AUTHORIZED), G7 전 결과 열람 금지
- TERMINAL_STATE(TASK_COMPLETE = NOT_DECLARED)
- GATE_TRANSITION_RULES의 나머지 항목
- G3a~G8의 순서와 승인 범위(G3b parent, G4b 4경로 외)
- BT4-FUTILITY-01의 Work Order·ERRATA와 산출물
- 사전등록 docs/research_bt4_futility_diag_preregistration.md
- config configs/bt4_futility_diag.toml
- pyproject.toml, requirements.txt, requirements-dev.txt
- .claude/**(guard·hook·settings)
- 그 밖의 FORBIDDEN_ACTIONS(의존성 추가 금지 포함)

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- TASK_TEST_VENV_EXCEPTION
  - TASK_VENV: C:/MoneyLab-bt4-futility-02/.venv (ignored, .gitignore:24)
  - TASK_PYTHON: C:/MoneyLab-bt4-futility-02/.venv/Scripts/python.exe
  - BASE_PYTHON: Python 3.14.8 Windows 실행 파일 하나.
    경로는 E3 Gate Authorization에 적고, E3-0에서 `--version`이 3.14.8인지 확인한다.
  - 허용 명령(E3, 각 1회, 이 순서, cwd = TARGET_WORKTREE):
    - E3-1 `<BASE_PYTHON> -m venv C:/MoneyLab-bt4-futility-02/.venv`
    - E3-2 `<TASK_PYTHON> -m pip install -r requirements-dev.txt`
    - E3-3 `<TASK_PYTHON> -m pip install -e . --no-deps`
  - CI(ci-tests.yml pytest job)의 venv 생성·설치 단계와 같은 구성이다.
  - 금지: pip 업그레이드, 다른 패키지 설치·제거·업그레이드,
    `--force-reinstall`, `--upgrade`, venv 재생성·교체.
  - 이 venv는 G2 재검증, G3c, G5·G6의 유일한 Python 실행 환경이다.
  - 이 task에서 C:/MoneyLab-mc-v06/.venv와 PYTHONPATH 주입은 더 이상 쓰지 않는다.
  - junction·symlink, guard·hook·settings 변경은 이 예외에 포함되지 않는다.
- LOCK(24개, requirements.txt와 requirements-dev.txt의 고정 버전)
  - DIRECT_RUNTIME(requirements.txt 직접 4개):
    requests==2.34.2, rich==15.0.0, python-dotenv==1.2.4, websockets==17.2
  - DIRECT_DEV(pyproject.toml:20 dev 4개):
    pytest==9.1.1, ruff==0.17.2, mypy==2.4.0, coverage==7.17.0
  - TRANSITIVE_RUNTIME(requirements.txt `# transitive` 8개):
    certifi==2026.7.22, charset-normalizer==3.5.2, idna==3.20, urllib3==2.8.0,
    markdown-it-py==4.2.0, mdurl==0.1.2, Pygments==2.21.0, colorama==0.4.6
  - TRANSITIVE_DEV(requirements-dev.txt의 나머지 8개):
    iniconfig==2.3.0, packaging==26.3, pluggy==1.6.0, ast_serialize==0.13.1,
    librt==0.16.0, mypy_extensions==1.1.0, pathspec==1.1.1, typing_extensions==4.16.0
  - 이름 비교는 정규화 이름(소문자, `[-_.]+` → `-`)으로 한다.
- E3-4 환경 검증(읽기 전용. V1~V11이 전부 PASS여야 E3 PASS다)
  - V1 platform.python_version() == "3.14.8"이다.
  - V2 sys.platform == "win32"이다.
  - V3 os.path.normcase(os.path.realpath(sys.executable))가
    os.path.normcase(os.path.realpath(TASK_PYTHON))와 같다.
  - V4 `<TASK_PYTHON> -m pip check`의 종료 코드가 0이다.
  - V5 DIRECT_RUNTIME 4개와 DIRECT_DEV 4개가 정확한 버전으로 설치돼 있다.
  - V6 `<TASK_PYTHON> -m pip freeze --all`의 전체 결과를 보고한다.
    - LOCK 24개가 전부 정확한 버전으로 있어야 한다.
    - LOCK, moneylab, pip, setuptools 밖의 배포판이 있으면
      UNEXPECTED_DISTRIBUTION으로 STOP하고 사용자가 판단한다.
    - pip·setuptools 버전은 보고만 한다.
  - V7 editable moneylab을 확인한다.
    - TASK_VENV site-packages의 moneylab 0.3.0 dist-info가 editable이다.
    - direct_url.json의 url이 TARGET_WORKTREE를 가리킨다.
    - editable .pth 또는 finder가 TARGET_WORKTREE/src를 가리킨다.
    - 실제 형식을 읽어 보고하며 추측하지 않는다.
  - V8 PYTHONPATH 없이 다음 모듈의 `__file__` realpath·normcase가
    TARGET_WORKTREE/src 아래다: `moneylab`,
    `moneylab.research.v06.futility_diag`, `moneylab.research.v06.futility_02`.
  - V9 PYTHONPATH가 셸과 os.environ 모두에서 설정돼 있지 않다.
  - V10 다음이 모두 성립한다.
    - tracked·staged 변경 0
    - `git ls-files .venv` 출력 0줄
    - `git check-ignore .venv` 종료 코드 0
  - V11 TARGET_WORKTREE에서 `git status --porcelain=v1 --untracked-files=all`의
    출력이 정확히 다음 두 줄이다(순서 무관).
    - `?? src/moneylab/research/v06/futility_02.py`
    - `?? tests/test_v06_futility_02.py`
    - `??`로 시작하지 않는 줄(tracked·staged 변경)이 하나라도 있으면 FAIL이다.
    - 위 두 줄 밖의 untracked 줄이 하나라도 있으면 FAIL이다.
    - 두 줄 중 하나라도 없으면 FAIL이다.
    - ignored 항목은 이 출력에 나오지 않으며 E3 기록에서 따로 보고한다.
- 실행 파일 identity
  - G2 재검증·G3c의 pytest, G5·G6의 D10 단계 0과 `--expected-python`은 TASK_PYTHON이다.
  - 다르면 G2·G3c는 STOP, G5·G6은 IDENTITY_FAILED 또는 STOP이다.
- T1 실행 명령: `<TASK_PYTHON> -m pytest -p no:cacheprovider -rfEs -q`
  - cwd = TARGET_WORKTREE, PYTHONPATH 미설정.
- G2 계속 조건
  - HEAD = Ce, V11 PASS, E3 PASS.
  - 이는 PASS 전 G2의 계속이며, README 적합성은 README_COMPATIBILITY를 따른다.
- G2 추가 변경(G2 재검증에서만)
  - futility_02.ALLOWED_FILES를 위 4경로로 바꾼다.
  - 이 집합과 D1 changed-path 판정을 확인하는 테스트를 test_v06_futility_02.py에 반영한다.
  - 그 밖의 정의는 바꾸지 않는다.
  - Ce 전에는 두 G2 파일을 바꾸지 않는다.
- C2: G3b의 C2 parent는 Ce다. Ce는 이 파일 하나만 추가한다.
- 승인 식별자(G2 재검증 이후):
  `GATE_AUTHORIZATION: BT4-FUTILITY-02 <GATE> WO@29e8e446a9a36ee2bad2aa674339f414c09bb24d ERRATA-001@<Ce SHA>`
- 삽입 gate(각 Gate Authorization 1건, 보고 후 STOP)
  - E1 ERRATA_CANDIDATE_FREEZE
    - 사용자가 최종 문안을 수락하고 README_COMPATIBILITY 결정을 한 뒤에만 한다.
    - 저장소 밖 C:/MoneyLab-Context-Intake/contract-review/BT4-FUTILITY-02/ERRATA-001.md
      1개를 Write 도구로 생성한다.
    - 내용은 수락된 문안에서 다음 두 줄만 바꾼 것이다.
      `STATUS: PROPOSED` → `STATUS: ACCEPTED`,
      `ACCEPTED_BY: NONE` → `ACCEPTED_BY: USER`
    - LF, UTF-8 BOM 없음, 줄 끝 공백 없음, tab 없음.
    - sha256·bytes·lines를 보고한다.
    - 생성 후 수정하지 않는다. 재발행은 새 파일명 ERRATA-001.r<N>.md로 한다.
  - E2 ERRATA_ISSUE
    - (1) 후보의 sha256·bytes·lines가 승인 값과 같다.
    - (2) TARGET 경로 docs/tasks/BT4-FUTILITY-02/ERRATA-001.md가 없다.
    - (3) 후보 바이트를 binary로 복사한다(줄끝 변환 없음).
    - (4) 복사본의 세 값을 다시 확인한다.
    - (5) `git add -- docs/tasks/BT4-FUTILITY-02/ERRATA-001.md`
    - (6) Ce 커밋 1회. 제목:
      "docs(bt4-futility-02): accept ERRATA-001 test environment contract"
    - (7) `git cat-file blob HEAD:docs/tasks/BT4-FUTILITY-02/ERRATA-001.md`의
      sha256이 후보 sha256과 같다.
    - (8) Ce 파일 집합 = 이 파일 하나, parent(Ce) = C1, V11 PASS.
  - E3 ENV_SETUP
    - E3-0 사전 확인: BASE_PYTHON 3.14.8, TASK_VENV 없음, PYTHONPATH 미설정,
      HEAD = Ce, V11 PASS, ignored 기준선 `git status --porcelain --ignored` 기록.
    - 그 뒤 E3-1 → E3-2 → E3-3 → E3-4 순서로 한다.

## README_COMPATIBILITY

README_COMPATIBILITY:
- 이 ERRATA는 docs/tasks/README.md(우선순위 2)를 바꾸지 않는다.
- G2 최초 진입은 HEAD = C1, porcelain 0줄에서 이루어졌다(G2 보고, CLAUDE_REPORTED).
- README §3 IMPLEMENTATION 진입 조건은 "HEAD가 C1(또는 그 후손), clean"이다.
- G2 계속 시점에는 두 G2 파일이 untracked로 있다.
- README는 중단된 IMPLEMENTATION의 계속 조건을 따로 정하지 않는다.
- 이 상태가 README에 맞는지는 이 ERRATA가 판정하지 않는다.
- 사용자가 E1 전에 결정하며, 맞지 않는다고 결정하면 이 문안은 발행하지 않는다.
- 사용자 결정(E1 전):
  - DECISION: OPTION_A
  - DECISION_SCOPE: CURRENT_STOPPED_G2_ONLY
  - UPPER_POLICY_COMPATIBILITY: USER_DECISION_RECORDED / NOT_DOCUMENTALLY_ESTABLISHED

## STOP_CONDITIONS

STOP_CONDITIONS (추가):
- E1: 사용자의 최종 문안 수락이 없다.
- E1: README_COMPATIBILITY에 대한 사용자 결정이 없다.
- E1: 후보 경로가 이미 있다.
- E2: 후보 세 값이 승인 값과 다르다.
- E2: TARGET 경로가 이미 있다.
- E2: 복사본 세 값이 후보와 다르다.
- E2: Ce 파일이 1개가 아니거나 parent(Ce)가 C1이 아니다.
- E2: blob sha256이 후보 sha256과 다르다.
- E2: 커밋 후 V11이 FAIL이다.
- E2: G2 파일이 변경되거나 stage됐다.
- E3-0: TASK_VENV가 있다, BASE_PYTHON이 3.14.8이 아니다,
  PYTHONPATH가 설정돼 있다, HEAD가 Ce가 아니다, 또는 V11이 FAIL이다.
- E3-1~E3-3: 종료 코드가 0이 아니다.
- E3-4: V1~V11 중 하나라도 FAIL이다.
- E3-4: UNEXPECTED_DISTRIBUTION이 있다.
- 공통: guard ASK 거절·DENY, 권한 거절.

## FAILURE_HANDLING

FAILURE_HANDLING:
- E3 각 단계에 다음을 기록한다.
  - 실행 명령
  - 종료 코드
  - 판정(PASS, FAIL, NOT_RUN)
  - TASK_VENV 존재 여부
  - 부분 설치 여부
  - E3-0 기준선 대비 새 ignored 산출물
  - tracked·untracked 상태
  - guard 이벤트
- 실패한 단계 뒤의 단계는 NOT_RUN이다.
- 실패 뒤 허용되는 것은 다음 읽기 전용 진단 1회뿐이다.
  - TASK_VENV 존재 확인
  - TASK_PYTHON이 있으면 `<TASK_PYTHON> -m pip freeze --all` 1회
  - `git status --porcelain=v1 --untracked-files=all`
  - `git status --porcelain --ignored`
- 자동 정리, 재시도, 삭제, 재생성을 하지 않는다.
- 부분 생성된 TASK_VENV의 처리(삭제 포함)는 사용자가 결정한다.
- 계약 변경이 더 필요하면 ERRATA-002로만 한다.

## ACCEPTANCE_CRITERIA

ACCEPTANCE_CRITERIA:
- AC-1: E1 후보 sha256 = E2 복사본 sha256 = Ce blob sha256이다.
- AC-2: Ce 파일 집합은 이 파일 하나이고 parent(Ce) = C1이다.
- AC-3: E3-4의 V1~V11이 전부 PASS다.
- AC-4: G2 재검증의 T1~T11이 TASK_PYTHON, PYTHONPATH 미설정에서 PASS다.

## BASELINE_IMPACT

BASELINE_IMPACT:
- .venv/, *.egg-info/, build/, __pycache__/는 ignored다(.gitignore:12·14·15·24).
- 소스, 테스트, Work Order, 사전등록, config, INPUT_HASH_MANIFEST에 영향이 없다.
- C2의 parent가 C1에서 Ce로 바뀐다.
- SOURCE_CODE_SHA(d2fcaf6), D13 E1의 base.sha, ANALYSIS_CODE_SHA = C2 규칙은 그대로다.

## SECURITY_IMPACT

SECURITY_IMPACT:
- guard·hook·settings는 바뀌지 않는다.
- 이 세션의 active guard는 C:/MoneyLab-bt4-futility-diag의 guard와 그 .venv다.
  TASK_VENV는 그 판정에 쓰이지 않는다.
- E3-2·E3-3은 guard `deps` ASK 대상이다(guard.py:297).
- E2의 `git commit`은 `git-commit` ASK 대상이다(guard.py:291).
- 사용자가 승인 창에서 각각 승인한다.
- 남는 위험: PyPI 다운로드에 hash 고정이 없다.
- 남는 위험: editable 빌드의 setuptools(>=69, 빌드 격리) 버전이 고정되지 않는다(CI와 같다).
- 남는 위험: ignored venv의 교체를 git이 잡지 못한다.

## APPROVAL

APPROVAL:
- 다음은 각각 사용자의 별도 승인으로 수행한다.
  - 최종 문안 수락
  - README_COMPATIBILITY 결정
  - E1, E2, E3
  - G2 재검증
- 이 파일의 STATUS가 ACCEPTED인 것은 사용자가 최종 문안을 수락했다는 기록이다.
- 효력은 Ce 커밋으로 생긴다.
- Ce 전에는 E3과 G2 변경을 시작하지 않는다.
