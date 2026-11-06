# Work Order: QUALITY-GATES-02 — 사전등록 프로파일 대비 연구 gate 보고서 구조 검증기

이 파일은 불변이다. C1 커밋 후 수정하지 않는다. 계약 변경은 `docs/tasks/QUALITY-GATES-02/ERRATA-<NNN>.md`(ACCEPTED)로만 한다.

## Metadata

WORK_ORDER_SCHEMA: moneylab.work_order/1
WORK_ORDER_CONTRACT_VERSION: v1.2
WORK_ORDER_ID: QUALITY-GATES-02
TASK_ID: QUALITY-GATES-02
TITLE: 연구 gate 보고서가 사전등록 프로파일의 구조 요구(가설, 필드, 다중성, 증거 등급, 금지 표현)를 갖췄는지 확인하는 결정적 순수 함수 검증기
VERSION: 1.0
STATUS: ISSUED
CANONICAL_BASE_SHA: 33f7e03cce76952c787483ef1f3f29cdda6e2d4d
CANONICAL_BASE_TREE: fd704651a8240f9002fec0102af4f583991aac65
CANONICAL_BASE_PARENTS: 5dcf70735f51159053b2387412d9a6ab18abfdb6 21bb6ab522e65cf680b837a33275da9e9061af6a
MERGE_EXPECTED_REMOTE_MAIN: 33f7e03cce76952c787483ef1f3f29cdda6e2d4d
REPOSITORY: swk3169/MoneyLab
TARGET_BRANCH: feature/quality-gates-02
TARGET_WORKTREE: C:/MoneyLab-quality-gates-02
WORKSPACE_SETUP: REQUIRED
INITIAL_GATE: WORKSPACE_SETUP
ACCEPTED_ERRATA: NONE
MERGE_METHOD: Create a merge commit
REQUIRED_CI_CHECKS: ci-tests / pytest (Windows)

## GATE_SEQUENCE

GATE_SEQUENCE: DESIGN_INVESTIGATION -> CONTRACT_REVIEW -> WORKSPACE_SETUP -> IMPLEMENTATION -> PRECOMMIT_AUDIT -> COMMIT -> CLEAN_COMMIT_E2E -> PUSH -> PR_CI -> MERGE -> POST_MERGE_AUDIT -> COMPLETE

DESIGN_INVESTIGATION과 CONTRACT_REVIEW(보완 포함)는 채팅에서 끝났다(파일 변경 없음).

## GATE_TRANSITION_RULES

GATE_TRANSITION_RULES:
- 앞으로는 한 gate씩, 명시적 Gate Authorization(`GATE_AUTHORIZATION: QUALITY-GATES-02 <GATE> WO@<C1 SHA>`)으로만 간다. WORKSPACE_SETUP 승인은 C1 전이므로 WO@ 대신 이 문구의 승인 사실을 명시한다. 각 gate 보고 후 멈춘다.
- 뒤로는 명시적 승인으로 IMPLEMENTATION까지만 간다.
- COMMIT 이후 수정은 새 커밋으로 한다. amend하지 않는다.
- 건너뛰기는 없다.

## ABSOLUTE_RULES

ABSOLUTE_RULES: 저장소 상위 규칙(CLAUDE.md, `.claude/` guard·hook·settings, docs/agent_workflow.md, 고정·사전등록 계약)을 참조한다. 복제하지 않고 바꾸지 않는다. guard deny는 우회하지 않는다.

## GOAL

GOAL: 사전등록이 요구한 보고 구조(가설 수·ID, 가설별 필드, SUPPORTED·WEAKENED 다중성 규칙과 수준, 전체 오류확률 상한, 특수 가설 규칙, 증거 등급, 금지 표현, 필수 보고 항목)를 연구 gate 보고서가 갖췄는지 확인하는 결정적 순수 함수 검증기를 추가한다. 구조 적합성만 확인하며 통계 계산의 정확성은 보증하지 않는다.

## BACKGROUND

BACKGROUND:
- BT4-FUTILITY-01은 CLOSED_INCOMPLETE로 종료됐다. COMPLETION_CRITERIA WO:466(G8a 보고의 사전등록 형식)이 FAIL이었고, 원인은 보고에서 WEAKENED 다중성 규칙(Bonferroni, 가설당 수준)과 특수 가설 규칙이 누락된 것이었다. 이 task는 그런 누락을 기계적으로 탐지하는 수단을 만든다.
- 이 task는 BT4-FUTILITY-01·BT4-FUTILITY-02의 판정, 상태, 산출물을 바꾸지 않고 소급 적용하지 않는다.
- 재사용 패턴: `src/moneylab/knowledge/validate.py`(정렬된 frozen Problem, 복구·추론 없음, 조용한 통과 없음), `src/moneylab/backtest/report.py`(알려진 schema 튜플, 미지 schema 거부, 결정적 JSON 규칙), `tests/test_knowledge_validate.py`(코드 안 합성 레코드). 패턴만 따르고 import하지 않는다.
- 사전등록 `docs/research_bt4_futility_diag_preregistration.md`는 프로파일이 표현해야 할 규칙의 형태 참고로만 쓴다. 그 값은 코드·테스트에 옮기지 않는다(D1).
- README §11에 따라 gate 보고는 채팅으로만 하므로, 검증기는 메모리 안 dict만 받는다.

## USER_DECISIONS

USER_DECISIONS (사용자 확정):
- D1 PROFILE: SYNTHETIC_ONLY. 실제 study(BT4 포함) 프로파일을 포함하지 않는다. 테스트는 합성 프로파일·보고서만 쓴다.
- D2 FORBIDDEN_TERMS: CASE_INSENSITIVE_WHOLE_TOKEN. 토큰은 ASCII `[A-Za-z0-9_]`의 최대 연속열이다(`re.ASCII`). 토큰을 casefold해 금지어와 같을 때만 탐지한다. `NOT_VALIDATED`, `uncalibrated`는 허용(다른 토큰)이고, `VALIDATED`, `calibrated`는 금지다(공백·구두점·하이픈 경계 포함).
- D3 MYPY_GATE: NO_EXPANSION. pyproject.toml을 바꾸지 않는다. 새 모듈은 required mypy gate에 넣지 않는다(ruff 필수 규칙은 적용된다).
- D4 UNKNOWN_SCHEMA: RETURN_PROBLEM_AND_STOP. 보고서 또는 프로파일 schema가 없거나 알려진 값이 아니면 그 Problem 하나만 담은 Result를 즉시 반환한다.
- D5 MERGE_BASE: MERGE_EXPECTED_REMOTE_MAIN_STRICT_MATCH. PUSH·MERGE 시점 원격 main이 MERGE_EXPECTED_REMOTE_MAIN과 다르면 STOP한다. 자동 rebase·merge·기준선 변경을 하지 않는다. 계약 변경이 필요하면 별도 ERRATA 승인 대상으로 보고한다.
- D6 WORK_ORDER_CREATION: DIRECT_AT_WORKSPACE_SETUP. 저장소 밖 후보 파일을 만들지 않는다. 최종 승인된 문구를 WORKSPACE_SETUP에서만 생성한다.
- D7 HYPOTHESIS_ID_DIAGNOSTICS: INDEX_ONLY. 보고서의 미지 ID·중복 ID는 실제 문자열을 출력하지 않고 `hypotheses[<index>]`로만 진단한다.

## SCOPE

SCOPE:
- `check_report(report, profile) -> Result` 순수 함수와 Problem·Result 타입
- schema 식별자, 허용 라벨, 오류 코드·고정 메시지 표 등 데이터 전용 상수 모듈
- 합성 fixture 기반 오프라인 테스트 파일 하나

## OUT_OF_SCOPE

OUT_OF_SCOPE:
- CLI(`src/moneylab/cli.py`, `__main__`), README.md, CLAUDE.md, docs/tasks/README.md, TEMPLATE
- pyproject.toml, requirements*.txt, configs/**, `.github/**`
- 실제 study 프로파일, 기존 보고서에 대한 소급 적용, 채팅 보고를 dict로 바꾸는 변환기
- 통계 계산 정확성 검증, 파일 읽기·쓰기, 네트워크, subprocess, 로깅
- BT4-FUTILITY-01·02의 판정·상태·산출물 변경, PR #40 변경

## ALLOWED_ACTIONS

ALLOWED_ACTIONS:
- WORKSPACE_SETUP(D6): 원격 main = CANONICAL_BASE_SHA 확인(`git ls-remote origin refs/heads/main`, 읽기). `git worktree add -b feature/quality-gates-02 C:/MoneyLab-quality-gates-02 <CANONICAL_BASE_SHA>`(새 경로만). 생성 직후 HEAD·tree·parents 확인. 승인된 문구 그대로 `docs/tasks/QUALITY-GATES-02/WORK_ORDER.md` 최초 생성(UTF-8, BOM 없음, LF, 끝 개행 1개). 그 경로만 `git add --`. C1 커밋 1개. REQUIRED_EVIDENCE의 HASH_DEFINITIONS에 따라 FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_MATCH를 보고한다. C1 이후 이 파일을 수정하지 않는다.
- IMPLEMENTATION: ALLOWED_FILES 생성, TEST_GATES 실행(오프라인)
- PRECOMMIT_AUDIT: 읽기와 감사만
- COMMIT: ALLOWED_FILES 세 경로만 명시해 `git add -- <경로>`, 커밋 1개(Ci)
- CLEAN_COMMIT_E2E: clean Ci에서 TEST_GATES 재실행. 저장소 안 파일 출력 없음
- PUSH: 원격 main = MERGE_EXPECTED_REMOTE_MAIN 확인 후 `git push -u origin feature/quality-gates-02` 1회
- PR_CI: Gate Authorization이 PR_CREATE: YES와 저장소·base(main)·head branch·head SHA·PR 제목·본문을 명시하면 `gh pr create` 1회(README §13). draft로 만들지 않는다
- MERGE: Gate Authorization이 MERGE_EXECUTE: YES와 PR 번호·head SHA를 명시하고 README §13 사전 검증 1–7을 모두 통과하면 `gh pr merge <N> -R swk3169/MoneyLab --merge --match-head-commit <SHA>` 1회
- POST_MERGE_AUDIT: main ref만 fetch(`git fetch origin main`, `--prune`·`--all` 없이), 구조 감사
- COMPLETE: 최종 보고(채팅)

## FORBIDDEN_ACTIONS

FORBIDDEN_ACTIONS:
- 승인된 gate 밖의 행위
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(C1_CREATION_EXCEPTION 제외)
- Work Order·ERRATA 수정(C1 이후 WORK_ORDER.md 수정 포함)
- `git add .`, `git add -A`, `--no-verify`, amend, force push(`--force`, `--force-with-lease`, `-f`, `+refspec`), reset, restore, stash, clean, rebase, cherry-pick, fetch --all, fetch --prune
- 원격 main 불일치 시 자동 rebase·merge·기준선 변경(D5)
- hooks·settings·`.claude` 변경 또는 guard 우회
- 다른 branch·worktree·untracked·ignored·reference 산출물 정리
- 연구 코드 실행, 연구 결과 파일 열람, `data/**` 접근
- 실제 study 결과값을 fixture·코드·메시지·보고에 쓰는 것
- 새 의존성 추가(표준 라이브러리만 쓴다)
- `gh pr edit`, `gh pr close`, CI 재실행, 자동 재시도

## ALLOWED_FILES

ALLOWED_FILES:
- A src/moneylab/research/report_conformance.py
- A src/moneylab/research/report_schema.py
- A tests/test_research_report_conformance.py

## PROTECTED_FILES

PROTECTED_FILES:
- docs/tasks/QUALITY-GATES-02/**
- docs/tasks/** (다른 task의 Work Order·ERRATA, README.md, TEMPLATE.md 포함)
- .claude/**
- .github/**
- CLAUDE.md, README.md, docs/agent_workflow.md
- pyproject.toml, requirements*.txt, configs/**
- docs/research_*preregistration*.md
- src/moneylab/cli.py, src/moneylab/__main__.py
- src/moneylab/research/__init__.py, src/moneylab/research/v06/**
- src/moneylab/research/*.py 중 src/moneylab/research/report_conformance.py와 src/moneylab/research/report_schema.py를 제외한 전부
- src/moneylab/knowledge/**, src/moneylab/backtest/**, src/moneylab/supervisor/**
- tests/conftest.py, tests/fixtures/**
- tests/** 중 tests/test_research_report_conformance.py를 제외한 전부
- data/**

INVARIANT: ALLOWED_FILES ∩ PROTECTED_FILES = ∅

C1_CREATION_EXCEPTION: `docs/tasks/QUALITY-GATES-02/**` 보호는 WORKSPACE_SETUP에서 승인된 문구로 `docs/tasks/QUALITY-GATES-02/WORK_ORDER.md`를 최초 생성하고 C1으로 커밋하는 행위 하나에는 적용되지 않는다(CLAUDE.md Work Order 불변 규칙, docs/tasks/README.md §3·§6). C1 이후에는 예외 없이 적용되며 WORK_ORDER.md는 수정하지 않는다. ERRATA 파일은 ACCEPTED ERRATA 커밋(Ce) 규칙으로만 생성한다. 다른 예외는 없다.

## DESIGN_CONTRACT

DESIGN_CONTRACT:
- DC1 위치·의존: 두 모듈은 `moneylab.research` 아래 둔다. 표준 라이브러리(`dataclasses`, `decimal`, `json`, `re`, `collections.abc`, `typing`)와 `moneylab.research.report_schema`만 import한다. `moneylab.providers`, `moneylab.knowledge`, `moneylab.backtest` 등 다른 moneylab 모듈, `subprocess`, `os`, `pathlib`, `logging`, `io`, 네트워크 모듈을 import하지 않는다. 모듈 import 시 부작용이 없다.
- DC2 schema: REPORT_SCHEMA = "moneylab.research.gate_report/1", PROFILE_SCHEMA = "moneylab.research.report_profile/1", RESULT_SCHEMA = "moneylab.research.report_conformance/1". KNOWN_REPORT_SCHEMAS·KNOWN_PROFILE_SCHEMAS는 각각 값 하나인 튜플이다.
- DC3 프로파일 구조: schema, study_id, hypothesis_ids(비어 있지 않은 고유 문자열 목록), required_hypothesis_fields, labels(SUPPORTED, WEAKENED, INCONCLUSIVE의 부분집합), reason_codes, evidence_grade, required_sections, multiplicity{SUPPORTED{method, fwer}, WEAKENED{method, fwer, per_hypothesis}, union_bound, special{<hypothesis_id>{components{<name>: level}}}}, forbidden_terms(비어 있지 않음). 프로파일 구조 오류는 QG-P01로 보고하고, 프로파일이 무효이면 보고서 검사를 하지 않는다.
- DC3a 프로파일 식별자: hypothesis_ids, required_hypothesis_fields, reason_codes, required_sections, special의 키와 component 이름은 모두 정규식 `^[A-Za-z][A-Za-z0-9_-]{0,31}$`(re.ASCII)에 맞아야 한다. 맞지 않으면 QG-P01이다. 이 규칙으로 10진 값(`.` 포함)이 where에 들어갈 수 없다. study_id는 where·message에 쓰지 않는다.
- DC4 보고서 구조: schema, study_id, evidence_grade, sections(list), hypotheses(list, 원소 dict {id, label, reason, 그리고 required_hypothesis_fields}), multiplicity(프로파일과 같은 모양). reason 키는 항상 있어야 한다(없으면 QG-C01). label이 INCONCLUSIVE이면 reason은 프로파일 reason_codes의 값이어야 하고, null이면 QG-C03, 목록 밖이면 QG-C04다. label이 INCONCLUSIVE가 아니면 reason은 null이어야 하고, 아니면 QG-C04다.
- DC5 수준 표기: 모든 수준(fwer, per_hypothesis, union_bound, special components)은 정규식 `^0\.[0-9]*[1-9]$|^1$`에 맞는 정규형 10진 문자열이다. 정규형이 아닌 같은 값(`"0.050"`, `"1.0"`, `".05"`, `"5E-2"`)과 float·int·bool·NaN·무한대는 불일치가 아니라 QG-T01이다. 정규형끼리의 일치는 문자열 완전 일치로 판단한다(정규형은 값마다 하나이므로 Decimal 동등성과 같다). 프로파일 내부 정합성은 `decimal.Decimal`로 계산한다: SUPPORTED.fwer + WEAKENED.fwer = union_bound(QG-F03), special components 합 = WEAKENED.per_hypothesis(QG-G03).
- DC6 검사 순서: (1) 인자 타입(DC10) (2) 프로파일 schema: 없거나 미지이면 QG-A03 하나로 즉시 반환(D4) (3) 보고서 schema: 없으면 QG-A01, 미지이면 QG-A02 하나로 즉시 반환(D4) (4) 프로파일 구조·식별자·정합성: 실패하면 프로파일 Problem만 반환 (5) 보고서 A–J: 모든 위반을 모은다. (1)–(5) 전체가 DC10a의 보호 안에서 실행된다.
- DC7 Problem과 고정 메시지: `@dataclass(frozen=True, order=True) Problem(code: str, where: str, message: str)`. report_schema는 `MESSAGES: dict[str, str]`(code → 고정 ASCII 메시지)를 정의하고, DC13의 모든 code가 정확히 하나의 메시지를 가진다. Problem.message는 항상 `MESSAGES[code]`다. 메시지는 입력에서 만들지 않는다(f-string·`%`·`format`·`repr`·`str(입력)` 금지). 표에 없는 code를 쓰는 것은 구현 오류이며 T24로 막는다. DC8–DC14와 함께 적용한다.
- DC8 where(필드 경로): schema 상수의 키 이름, DC3a를 통과한 프로파일 식별자, 정수 인덱스(`hypotheses[2]`), 고정 문자열 `"report"`·`"profile"`·`"check_report"`로만 만든다. 보고서에서 온 문자열(미지·중복 ID(D7), 미지 키, 라벨 값, reason 값, 금지어가 들어 있던 원문)은 where와 message에 넣지 않는다. 금지어 Problem의 where는 최상위 섹션 이름(schema 상수)과 프로파일 forbidden_terms 인덱스(`forbidden_terms[0]`)로만 표시한다.
- DC9 Result: `@dataclass(frozen=True) Result(problems: tuple[Problem, ...])`. problems는 중복을 제거하고 (code, where, message) 순으로 정렬한다. problems가 비면 `ok = True`, `exit_code = 0`이고, Problem이 하나라도 있으면(QG-X01 포함) `ok = False`, `exit_code = 1`이다. `to_dict()`는 {"schema": RESULT_SCHEMA, "ok", "exit_code", "problems": [{"code", "where", "message"}]}만 반환한다. `to_json()`은 `json.dumps(to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"`이다.
- DC10 입력 타입: 입력은 JSON 데이터 모델만 받는다. 정확한 타입 검사(`type(x) is …`)로 dict(키는 모두 str), list, str, int, float, bool, None만 허용한다. dict·list의 하위 클래스, 그 밖의 Mapping·Sequence, tuple, 다른 객체는 QG-T01이며 그 객체의 메서드(`__getitem__`, `__iter__`, `__eq__`, `__hash__`, `__str__`)를 호출하지 않는다. list가 필요한 곳의 str도 QG-T01이다. report 또는 profile 인자 자체가 정확히 dict가 아니면 `TypeError`를 던지고 메시지는 고정 문자열(인자 이름만)이다. 이 TypeError는 DC10a 밖, (1)단계에서만 발생한다.
- DC10a 내부 오류(QG-X01): DC6 (2)–(5) 실행 중 예상하지 못한 예외가 나면 QG-X01 Problem 정확히 하나(where = `"check_report"`, message = `MESSAGES["QG-X01"]`)만 담은 Result를 반환한다. 그 Result는 `ok = False`, `exit_code = 1`이다(DC9). 원 예외의 메시지·repr·traceback·args와 입력 값을 Result·Problem에 넣지 않고, 예외를 연쇄하지 않는다(`from None`, `__cause__`·`__context__` 보존 없음). 로깅하지 않는다. 정상 입력에서 QG-X01이 나오면 구현 결함이며 T29가 실패한다.
- DC11 불변·결정성: 입력을 수정하지 않는다(테스트에서 deepcopy와 비교). 복구·기본값 채우기·추론을 하지 않는다. 시각·난수·환경 변수·locale·파일 시스템에 의존하지 않는다. 같은 입력은 같은 `to_json()` 바이트를 낸다.
- DC12 금지 표현(D2): 보고서의 모든 str 값과 dict 키를 재귀적으로 훑는다. 토큰 규칙은 D2를 따른다.
- DC12a 순환·깊이: 재귀 탐색은 방문한 dict·list의 `id()` 집합과 최대 깊이 64를 쓴다. 순환을 만나거나 깊이를 넘으면 그 최상위 섹션에 QG-T01 하나를 내고 그 가지의 탐색을 멈춘다. RecursionError가 나지 않는다.
- DC13 오류 코드(A–J, 프로파일, 타입, 내부):
  - QG-T01 TYPE_INVALID
  - QG-X01 INTERNAL_ERROR
  - QG-P01 PROFILE_INVALID
  - QG-A01 REPORT_SCHEMA_MISSING, QG-A02 REPORT_SCHEMA_UNKNOWN, QG-A03 PROFILE_SCHEMA_UNKNOWN(없음 포함), QG-A04 STUDY_ID_MISMATCH
  - QG-B01 HYPOTHESIS_COUNT, QG-B02 HYPOTHESIS_ID_MISSING(프로파일 선언 ID가 보고서에 없음), QG-B03 HYPOTHESIS_ID_UNKNOWN, QG-B04 HYPOTHESIS_ID_DUPLICATE
  - QG-C01 FIELD_MISSING, QG-C02 LABEL_NOT_ALLOWED, QG-C03 REASON_REQUIRED, QG-C04 REASON_NOT_ALLOWED
  - QG-D01 SUPPORTED_FAMILY_MISSING, QG-D02 SUPPORTED_METHOD_MISMATCH, QG-D03 SUPPORTED_LEVEL_MISMATCH
  - QG-E01 WEAKENED_FAMILY_MISSING, QG-E02 WEAKENED_METHOD_MISMATCH, QG-E03 WEAKENED_LEVEL_MISMATCH, QG-E04 WEAKENED_PER_HYPOTHESIS_MISMATCH
  - QG-F01 UNION_BOUND_MISSING, QG-F02 UNION_BOUND_MISMATCH, QG-F03 PROFILE_BOUND_INCONSISTENT
  - QG-G01 SPECIAL_RULE_MISSING, QG-G02 SPECIAL_LEVEL_MISMATCH, QG-G03 PROFILE_SPECIAL_INCONSISTENT
  - QG-H01 EVIDENCE_GRADE_MISSING, QG-H02 EVIDENCE_GRADE_MISMATCH
  - QG-I01 FORBIDDEN_TERM
  - QG-J01 REQUIRED_SECTION_MISSING
- DC14 한계: PASS는 구조 적합성만 뜻한다. 값이 사전등록 절차대로 계산됐는지, 라벨이 옳은지는 확인하지 않는다. 모듈 docstring에 이 한계를 적는다.

## TEST_GATES

TEST_GATES:
- tests/test_research_report_conformance.py: 합성 프로파일·보고서를 코드 안에서 만들고 copy.deepcopy로 변형한다. 실제 study 값, 기존 BT4 결과, tests/fixtures 파일을 쓰지 않는다. 합성 값은 실제 결과와 혼동되지 않는 명백한 값(예: 가설 ID H-A…H-E, sentinel 문자열)을 쓴다.
- 필수 케이스(T01–T29, 각 번호 하나):
  T01 정상 보고서 → ok = True, exit_code = 0, problems 0
  T02 WEAKENED family 누락 → QG-E01
  T03 SUPPORTED family 누락 → QG-D01, method 불일치 → QG-D02, Holm 수준 불일치 → QG-D03
  T04 Bonferroni 가설당 수준 불일치 → QG-E04, WEAKENED family fwer 불일치 → QG-E03
  T05 WEAKENED method 불일치 → QG-E02
  T06 union bound 누락·불일치 → QG-F01·QG-F02
  T07 특수 가설 규칙 누락·수준 불일치 → QG-G01·QG-G02
  T08 프로파일 정합성 위반(합 불일치) → QG-F03·QG-G03, 보고서 검사 안 함
  T09 가설 개수 불일치 → QG-B01, 선언 ID 누락 → QG-B02, 미지 ID → QG-B03, ID 중복 → QG-B04(where는 인덱스만, D7)
  T10 필수 필드 누락(reason 키 포함) → QG-C01, 라벨 비허용 → QG-C02, INCONCLUSIVE reason null → QG-C03, INCONCLUSIVE reason 목록 밖·비INCONCLUSIVE reason non-null → QG-C04
  T11 증거 등급 누락·불일치 → QG-H01·QG-H02, study_id 불일치 → QG-A04
  T12 금지 표현: 중첩 문자열의 `VALIDATED`, `validated.`, `calibrated`, 키 이름 안 금지어 → QG-I01
  T13 오탐 방지: `NOT_VALIDATED`, `uncalibrated` → QG-I01 없음
  T14 필수 섹션 누락 → QG-J01
  T15 schema: 보고서 schema 없음 → QG-A01 하나만, 미지 → QG-A02 하나만, 프로파일 schema 없음·미지 → QG-A03 하나만(D4)
  T16 수준 타입: NaN·float·bool·int → QG-T01
  T17 dict가 아닌 인자 → TypeError, 메시지에 sentinel 없음
  T18 결정적 직렬화: 같은 입력 두 번 → to_json 바이트 동일, 입력 키 순서를 바꿔도 동일
  T19 정렬: 위반 입력 순서와 무관하게 problems 정렬 동일
  T20 입력 불변: 호출 전후 deepcopy와 같음
  T21 결과값 비노출: 보고서 값·미지 ID·미지 키·라벨·reason에 넣은 sentinel이 to_dict()/to_json()의 어떤 문자열에도 없음
  T22 예외 메시지 비노출: T17·T27의 예외·Problem 문자열에 sentinel 없음
  T23 import 경계: 두 모듈의 import가 DC1 허용 집합 안(ast 검사)
  T24 메시지 표: DC13의 모든 code가 MESSAGES에 정확히 하나 있고, 메시지가 ASCII이며, 모든 Problem.message == MESSAGES[code]
  T25 프로파일 식별자: DC3a 위반(예: 숫자·`.` 포함 hypothesis_id, section 이름) → QG-P01
  T26 비정규 수준: `"0.050"`, `"1.0"`, `".05"`, `"5E-2"` → QG-T01(불일치 코드 아님)
  T27 비정상 컨테이너: dict 하위 클래스·사용자 Mapping(메서드 호출 시 sentinel을 담은 예외를 던지도록 만든 것), tuple, list 자리의 str, str이 아닌 dict 키 → QG-T01, 예외 없음, 그 메서드가 호출되지 않음
  T28 순환·깊이: 자기 참조 dict·list, 깊이 65 중첩 → QG-T01, 예외·RecursionError 없음
  T29 내부 오류(DC10a): (a) T01–T28의 어떤 입력에서도 QG-X01이 없음. (b) 테스트가 report_conformance 내부 함수 하나를 monkeypatch로 sentinel을 담은 예외를 던지게 하면 결과는 QG-X01 하나(where = "check_report"), ok = False, exit_code = 1이고, sentinel이 to_dict()/to_json()에 없으며, 예외가 호출자에게 전파되지 않음
- 전체 pytest(`.\.venv\Scripts\python.exe -m pytest`): failed 0 / errors 0
- `.\.venv\Scripts\python.exe -m ruff check --no-cache --select E4,E7,E9,F src tests`: 위반 0
- `.\.venv\Scripts\python.exe -m mypy`(기존 gate, 범위 불변): exit 0
- `git diff --check` 깨끗함, 변경 파일 집합 = ALLOWED_FILES

## E2E_GATES

E2E_GATES: NOT_REQUIRED. 이 task는 CLI·파일 출력이 없다. 대체 확인: CLEAN_COMMIT_E2E에서 clean Ci 기준으로 TEST_GATES(대상 테스트 파일, 전체 pytest, ruff, mypy)를 다시 실행하고, 실행 전후 `git status --porcelain`이 비어 있음을 확인한다.

## REQUIRED_EVIDENCE

HASH_DEFINITIONS:
- FILE_SHA256: 작업 트리 파일 바이트의 SHA-256(소문자 hex 64자리).
- GIT_BLOB_OID: `git rev-parse <commit>:<path>`가 내는 Git 객체 ID. Git 객체 형식의 해시이며 SHA-256 값과 비교하지 않는다.
- BLOB_CONTENT_SHA256: `git cat-file blob <commit>:<path>`가 내는 바이트의 SHA-256. 보조 증거다.
- BLOB_CONTENT_MATCH: `git cat-file blob <commit>:<path>` 바이트와 작업 트리 파일 바이트가 바이트 단위로 같으면 YES, 아니면 NO. 서로 다른 해시 알고리즘의 값을 비교해서 판정하지 않는다.

REQUIRED_EVIDENCE (gate별 통과 증거와 확인 주체. 보고 key 목록은 REQUIRED_REPORT에 따로 있다):

| gate | GIT_VERIFIABLE | CLAUDE_REPORTED | INDEPENDENT | 통과 확인 |
|---|---|---|---|---|
| WORKSPACE_SETUP | `git ls-remote` 원격 main = CANONICAL_BASE_SHA; worktree 생성 직후 HEAD = CANONICAL_BASE_SHA, tree = CANONICAL_BASE_TREE, parents = CANONICAL_BASE_PARENTS; C1 SHA·tree; C1 parent = CANONICAL_BASE_SHA; C1 파일 집합 = {docs/tasks/QUALITY-GATES-02/WORK_ORDER.md}; FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_SHA256; BLOB_CONTENT_MATCH = YES | 문구가 승인본과 같음, clean | 사용자가 FILE_SHA256·C1 확인 | 사용자 |
| IMPLEMENTATION | 변경 파일 집합 ⊆ ALLOWED_FILES; PROTECTED diff 0; HEAD = C1 | T01–T29, 전체 pytest 수(passed/failed/errors/skipped), ruff, mypy exit 0 | 없음 | 사용자(보고 수락) |
| PRECOMMIT_AUDIT | 변경 집합 = ALLOWED_FILES(전부 A); `git diff --check`; PROTECTED diff 0; 세 파일 FILE_SHA256 | DC1–DC14 spot check, 결과값 부재 확인 | 없음 | 사용자 |
| COMMIT | Ci SHA·tree; Ci parent = C1; Ci 파일 집합 = ALLOWED_FILES; 세 파일 GIT_BLOB_OID; 세 파일 BLOB_CONTENT_MATCH = YES; 세 FILE_SHA256 = PRECOMMIT_AUDIT 값 | clean | 없음 | 사용자 |
| CLEAN_COMMIT_E2E | HEAD = Ci; 실행 전후 `git status --porcelain` 비어 있음 | TEST_GATES 재실행 결과 | 없음 | 사용자 |
| PUSH | 원격 main = MERGE_EXPECTED_REMOTE_MAIN; 원격 branch head = Ci | 없음 | 사용자가 GitHub branch 확인 가능 | 사용자 |
| PR_CI | PR base·head·head SHA; PR 커밋 {C1, Ci}·파일 4개 = PR 범위 | 없음 | REQUIRED_CI_CHECKS가 head SHA에서 SUCCESS(GitHub Actions) | 사용자(CI 화면) |
| MERGE | README §13 사전 검증 1–7(7은 MERGE_EXPECTED_REMOTE_MAIN), merge SHA | 사전 검증 기록 | 사전 검증 5: 사용자가 이 표의 IMPLEMENTATION·PRECOMMIT_AUDIT·CLEAN_COMMIT_E2E CLAUDE_REPORTED 증거와 PR_CI INDEPENDENT 증거를 수락 | 사용자 |
| POST_MERGE_AUDIT | merge parent1 = MERGE_EXPECTED_REMOTE_MAIN, parent2 = PR head; merge tree = merge-tree 재계산; first-parent 범위; ancestry; branch·worktree 보존 | 감사 기록 | 사용자 확인 | 사용자 |

- Claude가 실행한 결과는 INDEPENDENT로 쓰지 않는다(CLAUDE.md, docs/tasks/README.md §11).

## REQUIRED_REPORT

REQUIRED_REPORT:
- TASK_ID, GATE, WORK_ORDER_COMMIT, WORK_ORDER_SHA256(= C1 WORK_ORDER.md의 FILE_SHA256)
- HEAD·parent·tree, 변경 파일 집합, PROTECTED diff, worktree clean, diff --check
- WORKSPACE_SETUP: FILE_SHA256, GIT_BLOB_OID, BLOB_CONTENT_SHA256, BLOB_CONTENT_MATCH
- 그 gate의 REQUIRED_EVIDENCE 행과 각 값의 증거 등급(GIT_VERIFIABLE / CLAUDE_REPORTED / INDEPENDENT)
- PROPOSED_ERRATA, ISSUES
- GUARD_EVENTS
- DEVIATIONS
- RESULT_REREAD_COUNT, RESULT_CONTEXT_EXPOSURE
- <GATE>_PASS = YES / NO
- READY_FOR_<NEXT_GATE> = YES / NO

## STOP_CONDITIONS

STOP_CONDITIONS:
- base·HEAD·tree·parents가 기대와 다름
- Work Order 불일치: C1 WORK_ORDER.md가 승인 문구와 다르거나 BLOB_CONTENT_MATCH = NO, 또는 이후 gate에서 FILE_SHA256이 WORK_ORDER_SHA256과 다름
- C1 이후 WORK_ORDER.md 변경
- ALLOWED_FILES 밖 tracked 변경, PROTECTED_FILES 변경(C1_CREATION_EXCEPTION 제외), ALLOWED_FILES ∩ PROTECTED_FILES ≠ ∅
- ALLOWED_FILES의 A 표기와 base 상태 불일치(경로가 이미 있음)
- TARGET_BRANCH 또는 TARGET_WORKTREE가 이미 있음
- guard deny, 권한 창 거절
- 테스트 실패·에러, ruff 위반, mypy exit ≠ 0, TEST_GATES 항목 불일치, COMMIT의 BLOB_CONTENT_MATCH = NO
- 계약 모순, 상위 규칙과 충돌
- 예상하지 못한 untracked 파일
- 원격 main이 기대값과 다름(WORKSPACE_SETUP: CANONICAL_BASE_SHA, PUSH·MERGE: MERGE_EXPECTED_REMOTE_MAIN, D5). 필드를 고치지 않고, 자동 rebase·merge 없이, 별도 ERRATA 승인 대상으로 보고한다
- 구현에 실제 study 값이 필요해지거나 연구 결과 열람이 필요해짐
- ALLOWED_FILES 밖 변경(예: research/__init__.py export, pyproject)이 필요해짐

## COMPLETION_CRITERIA

COMPLETION_CRITERIA:
- ALLOWED_FILES 세 개가 DESIGN_CONTRACT DC1–DC14(DC3a, DC10a, DC12a 포함)대로 있다.
- TEST_GATES T01–T29와 전체 pytest·ruff·mypy·diff --check가 통과한다.
- PR이 merge commit으로 main에 합쳐지고 REQUIRED_CI_CHECKS가 head SHA에서 SUCCESS다.
- POST_MERGE_AUDIT가 REQUIRED_EVIDENCE의 POST_MERGE_AUDIT 행대로 PASS한다.
- BT4-FUTILITY-01·02의 판정·상태·산출물과 PR #40이 바뀌지 않았다.
- 실제 study 결과값이 코드·테스트·PR 본문·보고 어디에도 없다.

## ROLLBACK_POLICY

ROLLBACK_POLICY:
- Work Order는 C1 이후 불변이다. 계약 변경은 ACCEPTED ERRATA(Ce)로만 한다.
- 구현 문제는 명시적 승인으로 IMPLEMENTATION에 돌아가 새 커밋으로 고친다. amend·reset·force push를 쓰지 않는다.
- push 후 추가 커밋의 push도 별도 PUSH 승인이 필요하다.
- merge 후 문제는 revert하지 않고 새 Work Order로 다룬다.
- branch·worktree는 COMPLETE 뒤에도 지우지 않는다.

## PR_POLICY

PR_POLICY:
- PR 하나, base main, head feature/quality-gates-02, draft 아님.
- PR 범위 = ALLOWED_FILES ∪ docs/tasks/QUALITY-GATES-02/**. 커밋은 C1(Work Order)과 Ci(구현). ERRATA가 생기면 Ce가 추가된다.
- PR 제목·본문은 PR_CI Gate Authorization에서 확정한다. 본문에 연구 결과값을 쓰지 않는다.

## MERGE_POLICY

MERGE_POLICY:
- MERGE_METHOD: Create a merge commit(`--merge`)만. `--admin`, `--auto`, `--squash`, `--rebase`, `--delete-branch`, `--force` 금지.
- README §13 사전 검증 1–7을 모두 통과해야 한다. 7의 기대값은 MERGE_EXPECTED_REMOTE_MAIN이고 엄격 일치다(D5).
- 사전 검증 5가 요구하는 추가 증거는 REQUIRED_EVIDENCE 표의 MERGE 행에 정의된 것이다.
- merge 후 보고하고 멈춘다. POST_MERGE_AUDIT는 별도 승인으로 한다.
