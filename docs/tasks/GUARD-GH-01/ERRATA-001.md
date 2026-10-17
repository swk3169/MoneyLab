# ERRATA: GUARD-GH-01 ERRATA-001

이 파일은 불변이다. 추가 변경은 다음 번호의 ERRATA로 한다.

ERRATA_SCHEMA: moneylab.errata/1
ERRATA_ID: GUARD-GH-01-ERRATA-001
TASK_ID: GUARD-GH-01
TARGET_WORK_ORDER: docs/tasks/GUARD-GH-01/WORK_ORDER.md @ 8dd83a0194ebda8917e0beb0ab98332027a7ce41 (sha256 1dc4cba03c00a4a47c035f75b0ed197556422df48a57f5ac0759442b30878f38)
SUPERSEDES_ERRATA: NONE
STATUS: ACCEPTED
ACCEPTED_BY: 사용자, 2026-10-17

## CHANGED_FIELDS

CHANGED_FIELDS:
- DESIGN_CONTRACT.D3
- SECURITY_INVARIANTS.G7
- CLASSIFICATION_MATRIX.D
- TEST_GATES.T5

## RATIONALE

RATIONALE: D3는 GH_PUBLISHED_BODY_PAYLOAD를 "`normalize()`를 거친" 뒤 `env`/`trading`으로 검사하라고 하면서, 게시 본문 산문의 `.env.local`, `place_order`, `UPBIT_ACCESS_KEY` 등이 DENY되어야 한다고 정한다. 그런데 `normalize()`는 입력이 `\s*git\s+commit`으로 시작하면 `_HEREDOC`과 `_COMMIT_MSG`로 텍스트를 제거하는 기존 분기를 갖고 있고, 이 분기는 D8/G11로 바꿀 수 없다. 그래서 payload 첫 줄이 `git commit`처럼 보이는 산문이면 payload 안의 `-m '…'`/`--message '…'` 인용 텍스트와 heredoc 형태 텍스트가 검사 전에 지워져 D3의 DENY 요구와 G7이 지켜지지 않는다. IMPLEMENTATION 중 offline·in-process 분류 테스트로 재현했다: 아래 세 payload가 모두 기대 DENY 대신 (ask, github)였다. 이 ERRATA는 이 D3/G7 모순만 해소한다.

## REPLACEMENT_CONTRACT

REPLACEMENT_CONTRACT:
- DESIGN_CONTRACT.D3: D3 게시 본문의 secret 보호:
  - 기존 DENY_RULES 중 `env`(`(^|[\s/=<>])\.env(?!\.example)\b`)와 `trading`(정규식 전체, 분해하지 않음)을 PAYLOAD_SAFE_NORMALIZATION을 거친 GH_PUBLISHED_BODY_PAYLOAD에 그대로 적용한다.
  - PAYLOAD_SAFE_NORMALIZATION: GH_PUBLISHED_BODY_PAYLOAD는 `normalize()`의 `git commit` 메시지 제거 동작을 거치지 않는다. 기존 `env`/`trading` 탐지기에 필요한, 텍스트를 지우지 않는 정규화만 쓴다. 허용: 소문자화, 백슬래시→`/`, 기존 탐지 의미와 같은 따옴표·backtick·caret 문자 정규화, 연속 `/` 축약, 공백 정리, D1 실행 파일 축약, 그리고 임의의 게시 산문을 지울 수 없는 경우에 한해 git global option 정규화. 금지: `_HEREDOC` 제거, `_COMMIT_MSG` 제거, 입력이 `git commit`으로 시작할 때의 `normalize()` 특수 분기, 그 밖에 `env`/`trading` 검사 전에 임의의 게시 산문을 제거하는 모든 변환.
  - 보안 불변: 기존 `env` 또는 `trading` 탐지기 매치에 기여할 수 있는 GH_PUBLISHED_BODY_PAYLOAD의 모든 바이트는 payload 정규화 후에도 의미상 탐지 가능해야 한다.
  - OPERATIONAL_COMMAND_TEXT의 정규화는 바뀌지 않는다(기존 `normalize()` 그대로).
  - 결과로 게시 본문 산문의 `place_order`, `/v1/orders`, `.env.local`, `UPBIT_ACCESS_KEY`, `seed phrase`, `private_key`, `mnemonic` 등은 DENY된다(사용자 승인된 보수적 동작). payload가 `git commit`처럼 보이는 산문으로 시작해도 같다.
  - 검사 순서: OPERATIONAL_COMMAND_TEXT의 DENY_RULES → payload의 `env`/`trading` → OPERATIONAL_COMMAND_TEXT의 나머지 검사(PROTECTED/MUTATE, DELETE_MOVE, ASK_RULES, INLINE_CODE, untracked script, `_moneylab`). payload DENY는 이후 operational 판정보다 우선한다. 보고 rule 이름은 기존 `env` 또는 `trading`이다.
  - 그 밖의 규칙(git/clock/registry/power/exec/hooks DENY, `protected-path`, `protected-word`, `locked`, `inline-code`, `untracked-script`, `_moneylab`, `check_command` 첫 줄의 `git branch -D` 검사)은 payload를 검사하지 않고 OPERATIONAL_COMMAND_TEXT에만 적용한다.
  - 새 탐지기, 새 rule 이름, 새 `Decision` rule 문자열을 추가하지 않는다(`tests/test_skills.py`의 문서·rule 이름 일관성 유지). `env`/`trading` 정규식은 바꾸지 않는다.
  - D8/G11은 바뀌지 않는다: `_HEREDOC`, `_COMMIT_MSG`, `normalize()`의 `git commit` 분기는 바이트 단위로 바꾸지 않는다.
- SECURITY_INVARIANTS.G7: G7: `env`와 `trading` DENY 규칙은 PAYLOAD_SAFE_NORMALIZATION(D3)을 거친 payload도 검사하고, 매치되면 operational 판정보다 우선해 DENY한다. payload 정규화는 `git commit` 메시지 제거 동작(`_HEREDOC`, `_COMMIT_MSG`, `normalize()`의 `git commit` 분기)이나 그 밖의 산문 제거 변환을 쓰지 않으며, `env`/`trading` 매치에 기여할 수 있는 payload 바이트를 지우지 않는다.
- CLASSIFICATION_MATRIX.D: D. 게시 본문 secret → DENY (합성 placeholder만 사용):
  - 인용 본문 `see .env.local` → (deny, env)
  - 인용 본문 `UPBIT_ACCESS_KEY placeholder` → (deny, trading)
  - 인용 본문 `seed phrase placeholder` → (deny, trading)
  - 인용 본문 `call place_order here` → (deny, trading)
  - 인용 본문 `git commit -m '.env.local'` → (deny, env)
  - 인용 본문 `git commit -m 'call place_order here'` → (deny, trading)
  - 인용 본문 `git commit is how we ship\nsee -m 'UPBIT_ACCESS_KEY placeholder'` → (deny, trading)
- TEST_GATES.T5: T5 게시 payload secret: 매트릭스 D → `env` 또는 `trading`으로 deny. `git commit`으로 시작하는 payload 3건을 포함한 매트릭스 D 전체는 일반 PASS 요구이며 xfail로 표시하지 않는다. GUARD-HEREDOC-01용 기존 strict xfail(T11)은 바뀌지 않는다.

## SCOPE

SCOPE (이 ERRATA가 바꾸지 않는 것):
- D1, D2, D4, D5, D6, D7, D8, D9, D10
- G1, G2, G3, G4, G5, G6, G8, G9, G10, G11, G12 (G7은 위 정규화 모순 해소만 명확히 한다)
- GitHub ASK 동작(`github` rule), gh heredoc 분리 자격 규칙, fail-closed 동작
- `.claude/settings.json`, protected-path 동작(`sed` 포함)
- 활성 guard activation, GUARD-HEREDOC-01
- ALLOWED_FILES, PROTECTED_FILES, GATE_SEQUENCE, 그 밖의 모든 Work Order 필드
- 새 탐지기나 guard rule은 승인되지 않는다. `env` rule을 넓히거나 `trading` rule을 바꾸지 않는다.

## CONSTRAINTS

CONSTRAINTS:
- 우선순위 1-3(안전·도구, 저장소 절대 규칙, 고정·사전등록 계약)은 바꾸지 않는다.
- ALLOWED_FILES ∩ PROTECTED_FILES = ∅ 를 유지한다.
