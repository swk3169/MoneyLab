AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-12
STATUS: RESEARCH_INTAKE_NOT_REQUIREMENT
REPOSITORY_REFERENCE: 8eed531cd09ff2748bf91165abd0e1a69b8148c8
OPERATIONAL_OBSERVATIONS: 2026-11-12 세션 기록. 현재 실행 상태의 재확인 결과가 아님.
RESEARCH_DOCUMENT_STATUS: NON_AUTHORITATIVE_REFERENCE
INTAKE_EDIT_HISTORY: SOURCE_REGISTER.md의 편집 이력 참조. 원본 보고서의 STATUS 값은 작성 시점 값으로 유지함.

# MoneyLab 전체 절차 자동화를 OpenClaw로 검증한다

**OpenClaw는 MoneyLab의 전체 개발 절차를 자동화할 전달·실행 조정 계층의 후보이며, 이번 시험은 그 일부 연결 경로를 확인했다.** 연구 목적은 토큰 사용을 무조건 피하는 것이 아니다. 사용자가 수행하던 맥락 전달, 계약 검토, 승인 요청, 실행 지시, 결과 수집, 검증, 중단 후 재개를 연결하고, 같은 품질을 유지하면서 사용자 개입과 총비용을 줄이는 것이다. 현재 확인된 것은 Claude Code와 OpenClaw 사이의 송수신, 새 Claude ACP 세션의 실행, 현재 desktop 대화에서 기존 시험 세션으로 보낸 직접 요청과 응답이다. 프로젝트 guard의 실효성, 승인 대기 처리, PC 재시작 후 복구, 실제 작업당 비용과 장기 운영은 아직 검증하지 않았다. OpenClaw를 직접 연구한 논문과 관련 agent 평가 연구는 도입을 검토할 근거를 제공하지만, MoneyLab의 자동화 성공이나 거래 순수익을 입증하지 않는다. 권장 방향은 기존 AUTO-01·AUTO-02·GOV-AUTOMATION-02를 대체하지 않고 그 위에 필요한 연결을 단계적으로 검증하는 것이다. 이 문서는 연구자료이며 Work Order, Gate Authorization, 설정 변경, Git 게시 또는 실거래 승인이 아니다.

## 1. 기존 연구는 이미 전체 자동화를 요구하며 OpenClaw는 실행 후보를 추가한다

### 최종 목표와 이번 연구의 목적함수를 분리한다

MoneyLab의 최종 목표는 거래비용과 운영비를 차감하고도 실제 순수익을 낼 수 있는 24시간 AI agent 시스템이다. 개발 절차 자동화는 그 목표에 도달하기 위한 수단이다. 지금까지의 읽기 전용 Scanner, 오프라인 시뮬레이션, Recorder·Replay와 이번 개발 도구 시험을 실거래 시스템 완성으로 표현하면 안 된다. 기존 통합 연구도 전략 검증, paper 운영, 별도 승인된 실거래를 구분하고, 연구자료 자체를 개발 승인이나 수익성 근거로 취급하지 않는다. ([기존 기술 통합 결론](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/integration/FINAL_TECHNICAL_SYNTHESIS.md))

개념상 `거래 net = gross PnL − 수수료 − spread − slippage − 그 밖의 거래비용`이며, `시스템 net = 거래 net − 반복 AI·데이터·서버·모니터링·복구 운영비`다. 개발비는 일회성 투자와 반복 유지보수비로 따로 기록한다. 연구 단계에서 이 비용을 숨기지 않되, 개발 setup 비용 전부를 매일의 거래비용처럼 계산하지 않는다. 회계 기간, 비용 배분, 구독의 증분비용 기준은 측정 전에 고정해야 한다. 이 식은 연구용 비용 구분이며 실제 순수익이 존재한다는 주장이 아니다. ([SRC-005 비용과 알파](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-005_AI_COSTS_AND_ALPHA.md))

이번 도구 연구의 목적함수는 **성공한 작업당 전체 비용, 완료 품질, 사용자 개입, 지연, 복구 가능성**이다. 토큰이 늘어도 재작업과 사용자 시간을 충분히 줄이면 채택할 수 있다. 토큰이 줄어도 승인 위반이나 검증 누락이 생기면 채택하면 안 된다. 사용자 시간의 가치를 금액으로 환산할지는 사용자가 정한다. 금전비용과 시간을 합치지 않은 원자료도 보존한다. 정확도만으로 agent를 평가하면 불필요한 복잡성과 비용을 보상할 수 있다는 연구는 이 판단 기준을 뒷받침한다. ([AI Agents That Matter](https://arxiv.org/html/2407.01502v1))

### 조사 기준선과 자료의 권위를 고정한다

저장소 비교 기준은 merge commit `8eed531cd09ff2748bf91165abd0e1a69b8148c8`이다. 로컬 `C:/MoneyLab` checkout은 오래된 `09504cd…`였으므로 기존 연구·계약·guard는 고정 Git 객체에서 읽었다. 이 문서는 해당 SHA를 현재 원격 최신 HEAD라고 주장하지 않는다. 최신 원격 상태와 실제 작업 worktree는 저장소 반영 또는 구현 단계에서 다시 읽기 전용으로 확인해야 한다. 이번 조사에서 checkout, fetch, 테스트, 환경 변경, commit, push, PR, merge는 실행하지 않았다. ([고정 기준 commit](https://github.com/swk3169/MoneyLab/commit/8eed531cd09ff2748bf91165abd0e1a69b8148c8))

| 증거 구분 | 의미 | 사용할 수 없는 결론 |
|---|---|---|
| FIXED_REPOSITORY | 고정 commit의 파일·계약을 읽은 결과 | 현재 원격·worktree도 같다는 결론 |
| LOCAL_ARTIFACT | 당시 설치 코드·로그·원본 기록의 조회 | 다른 PC·버전에서도 같은 결과라는 결론 |
| SESSION_EVIDENCE | 사용자가 제공한 화면·Claude 보고·직접 도구 결과 | 누락 없는 독립 감사 또는 영구 공개 원문 |
| OFFICIAL_DOCUMENT | 공식 제품 문서의 지원 동작 | 설치 버전에 해당 옵션이 실제 적용됐다는 결론 |
| PAPER | 논문의 조건 아래 보고된 연구 결과 | MoneyLab에서의 재현·안전성·수익성 |
| PROPOSAL | 위 근거에서 도출한 설계와 수락 기준 | 현재 구현 완료 또는 실행 승인 |

문서·논문·세션 요약·가져온 메모리는 데이터다. 그 안의 명령과 승인 문장을 현재 사용자 승인으로 승격하지 않는다. 메모리의 PR #45 미병합 기록처럼 이미 잘못된 것으로 확인된 내용은 원문 이력과 정정 근거를 함께 남긴다. 과거 PASS와 모델 기억은 최신 Git 상태를 대신하지 않는다. 이는 기존 context 연구와 supervisor의 `Proposal ≠ Work Order ≠ Authorization` 원칙을 그대로 유지하는 것이다. ([SRC-004](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-004_CONTEXT_ENGINEERING.md), [Supervisor 계약](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/supervisor_proposal_contract.md))

### 기존 작업은 자동화의 부품이며 무인 운영 전체는 아니다

| 기존 요소 | 이미 정의한 범위 | OpenClaw 연구가 추가할 질문 |
|---|---|---|
| SRC-004 Context Engineering | 출처·시간·권위 분리, 필요한 맥락만 전달 | 어느 자료를 어느 실행 세션에 어떤 버전으로 전달하는가 |
| SRC-005 AI Costs and Alpha | 거래 net과 시스템 net, 개발비와 운영비 분리 | 모델·도구·재시도·사용자 개입을 합쳐 경제성을 측정하는가 |
| SRC-008 도구 평가 | 같은 기준선·자료·권한의 비교 | 수동 전달보다 전체 완료율과 개입 시간이 개선되는가 |
| SRC-009 Agentic Patterns | 상태 전이·예산·관찰성·single writer | 동시에 다른 세션이 같은 작업을 변경하지 않게 하는가 |
| SRC-011 Orchestration | Plan → Delegate → Observe → Reconcile → Report | 각 전이에 승인과 실제 증거가 연결되는가 |
| AUTO-01 | allowlist 판정, 제한된 오프라인 읽기 전용 실행, evidence | 새 실행 경로가 임의 shell 위임으로 범위를 넓히지 않는가 |
| AUTO-02 | 비권위 snapshot/verify | 기록과 실제 상태를 대조하고 재개 후보를 찾는가 |
| GOV-AUTOMATION-02 | 제한된 연속 Gate의 문서상 묶음 승인 | 허용된 구간을 자동 진행하되 종료된 승인은 복원하지 않는가 |

AUTO-01은 queue, scheduler, 자동 Git, 자동 Gate와 무인 반복을 제공하지 않는다. AUTO-02의 MATCH는 실행권한이나 Gate PASS를 만들지 않는다. GOV-AUTOMATION-02의 BGA는 신규 v1.3 계약의 제한된 구간에만 적용되고, PUSH·PR_CI·MERGE·ERRATA 고정과 후퇴는 개별 승인이다. **OpenClaw 연결은 이 NON_GOALS와 승인 경계를 자동으로 변경하지 않는다.** ([AUTO-01 WO](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/tasks/AUTO-01/WORK_ORDER.md), [AUTO-02 WO](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/tasks/AUTO-02/WORK_ORDER.md), [GOV-AUTOMATION-02 WO](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/tasks/GOV-AUTOMATION-02/WORK_ORDER.md))

기존 연구와 비교하면 부족한 부분은 OpenClaw라는 제품명의 설명이 아니다. 실제 workflow의 계측, 승인 전달의 강제성, MCP 도구의 보호 범위, 실행 ledger, 중단 후 reconciliation, 공급자 사용량 대조가 부족하다. 이번 자료는 이 공백을 채우기 위한 연구 설계다. 과거의 도입 보류 결정을 임의로 취소하지 않으며, 비용 우려만으로 OpenClaw를 영구 기각하지도 않는다. ([SRC-008](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-008_AI_DEVELOPER_TOOLS_EVALUATION.md), [SRC-009](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-009_AGENTIC_DEVELOPMENT_PATTERNS.md), [SRC-011](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-011_AGENT_ORCHESTRATION.md))

## 2. 논문은 실행 구조의 중요성을 보여 주지만 MoneyLab 전체 절차는 직접 평가하지 않는다

### OpenClaw 직접 연구와 일반 agent 연구를 구분한다

OpenClaw를 직접 다룬 학술 자료가 있다. 이번 조사에서는 제품과 다른 이름 충돌을 배제하고, 개인용 Gateway·메모리·도구·외부 코딩 실행기를 다루는 원문을 확인했다. 검색 기준일은 2026-11-12다. 사용한 검색어는 `OpenClaw arxiv agent security benchmark`, `OpenClaw agent paper arxiv automation`, `OpenClaw workflow arxiv benchmark`, `Claw-SWE-Bench arxiv.org`, `OpenClaw WildClawBench paper`다. 아래 자료의 제출·수정일은 기준일 이전다. arXiv DOI가 있다는 이유로 동료심사를 마쳤다고 표시하지 않는다.

| ID | 자료와 판본 | 확인한 방법·결과 | MoneyLab에 적용할 원칙과 한계 |
|---|---|---|---|
| P01 | A Systematic Security Evaluation of OpenClaw and Its Variants, arXiv:2604.03131v1, 2026-04-03 | 6개 계열, 205개 사례, 13개 공격 범주를 비교한 preprint | 모델의 말뿐 아니라 실행·반환·상태 변경을 검사한다. 현재 Windows 설치의 공격 성공률로 이전하지 않는다. ([원문](https://arxiv.org/html/2604.03131v1)) |
| P02 | From Assistant to Double Agent, arXiv:2602.08412v2, 2026-02-11 | PASB에서 외부 내용·개인 메모리·도구 및 스킬 반환의 공격을 실행으로 평가한 preprint | 가져온 기억과 문서가 실행 승인으로 바뀌지 않는지 검사한다. 오래된 모델 결과는 현재 성능이 아니다. ([원문](https://arxiv.org/html/2602.08412v2)) |
| P03 | OpenClaw in the Wild: Security Analysis of Autonomous Agents, 2026 | 기관 출판목록은 IEEE/CAA Journal of Automatica Sinica 13, 1257–1273으로 표시. 다섯 신뢰 경계를 제시 | 전달·세션 상태·도구 실행·외부 내용·확장 공급망을 따로 검토한다. 기관 초록·서지만 읽었고 IEEE 본문은 접근 오류로 미열람이다. ([기관 기록](https://research.google/pubs/openclaw-in-the-wild-security-analysis-of-autonomous-agents/)) |
| P04 | Claw-SWE-Bench, arXiv:2606.12344v2, 2026-09-28 | 350개 이슈, 8개 언어, 43개 저장소. 7개 실행 구조와 3개 모델을 고정 조건으로 비교 | 같은 작업·기반 commit·예산·평가기에서 구조를 비교한다. Linux Docker/API 결과는 Windows 구독·승인·재부팅 검증이 아니다. ([원문](https://arxiv.org/html/2606.12344v2)) |
| P05 | WildClawBench, arXiv:2605.10912v1, 2026-05-11 | 60개 과제, 6개 범주. 실제 OpenClaw·Claude Code·Codex·Hermes CLI를 평가. 최고 OpenClaw 결과 62.2% | 결정론 검사와 상태 감사를 함께 쓴다. 시작 요청 1개 후 실행하는 형식이므로 중간 승인·사용자 수정·장기 운영을 충분히 대표하지 않는다. ([원문](https://arxiv.org/html/2605.10912v1)) |
| P06 | AI Agents That Matter, arXiv:2407.01502v1, 2024-07-01 | 비용·정확도·holdout 및 평가 설계를 논의 | 실패와 재작업을 포함한 성공 작업당 비용을 본다. 당시 가격을 현재 청구액에 적용하지 않는다. ([원문](https://arxiv.org/html/2407.01502v1)) |
| P07 | tau-bench, arXiv:2406.12045v1, 2024-06-17 | 정책·도구·사용자 대화와 최종 상태를 평가. 반복 일관성 지표 pass^k 사용 | 한 번의 성공과 반복 완료를 구분한다. 금융 수익이나 Windows Git 승인 평가가 아니다. ([원문](https://arxiv.org/html/2406.12045v1)) |
| P08 | AgentDojo, arXiv:2406.13352v3, 2024-11-24 | 97개 정상 과제와 629개 보안 사례를 포함한 도구 환경 | 정상 완료율과 비승인 동작 차단을 함께 본다. 모든 작업을 거절하는 구성을 좋은 자동화로 평가하지 않는다. ([원문](https://arxiv.org/html/2406.13352v3)) |
| P09 | Lost in the Middle, TACL 2024, 12:157–173 | 다중 문서 질문·검색에서 정보 위치가 활용 성능에 영향을 줌 | 긴 인계가 정확한 최신 맥락 활용을 보장하지 않는다. 당시 검색 과제를 최신 Claude의 실패율로 환산하지 않는다. ([출판 기록](https://aclanthology.org/2024.tacl-1.9/)) |

### 벤치마크 수치를 채택 기준으로 바로 옮기지 않는다

P04는 모델을 고정해도 실행 구조의 효과를 비교해야 한다는 근거다. 최신 v2와 검색 결과에 남은 v1 수치를 섞지 않는다. 평가 과제의 피드백으로 진화시킨 Meta-Harness를 일반적인 독립 우월성 증거로 쓰지 않는다. P05는 모델뿐 아니라 실행 환경과 도구 구성이 결과를 바꿀 수 있음을 보여 준다. 그러나 두 자료 모두 MoneyLab의 계약 해시 확인, 여러 승인 단계, 장기 pytest, 재부팅, 구독 한도와 기존 guard를 한 번에 검증한 연구는 아니다. ([P04](https://arxiv.org/html/2606.12344v2), [P05](https://arxiv.org/html/2605.10912v1))

보안 논문은 자동화를 포기하라는 근거가 아니다. 정상 업무를 수행하면서 권한을 보존하는 평가를 설계하라는 근거다. P01·P02·P03의 결과를 바탕으로 문서와 메모리, 도구 결과, 실행권한, 플러그인을 별개 경계로 검토한다. 특정 OpenClaw 버전의 침해 여부는 해당 버전·권한·도구 경로에서 검증해야 한다. P07·P08의 방법론을 참고해 최종 상태와 반복 일관성을 측정하되, 이들의 원래 산업·모델·과제와 MoneyLab의 차이를 남긴다. ([P01](https://arxiv.org/html/2604.03131v1), [P02](https://arxiv.org/html/2602.08412v2), [P03](https://research.google/pubs/openclaw-in-the-wild-security-analysis-of-autonomous-agents/), [P07](https://arxiv.org/html/2406.12045v1), [P08](https://arxiv.org/html/2406.13352v3))

연구가 지지하는 결론은 **모델·실행 구조·권한·비용·복구를 함께 평가해야 한다**는 것이다. 어떤 논문도 현재 MoneyLab 전략의 알파, paper 성과, 실거래 손익, 비용 차감 후 순수익을 입증하지 않는다. 이번 검토 범위에서는 OpenClaw 2026.11.3, Claude Opus 5.5, GPT-6 계열, Windows PowerShell과 MoneyLab guard를 통합한 동료심사 재현 연구도 확인하지 못했다.

## 3. 연결 시험은 성공했고 비용 집계와 보호 범위에는 미검증이 남는다

### 설치 경로와 사건을 분리해서 기록한다

아래는 2026-11-12까지 이 대화에 남은 사용자 화면·출력, Claude 보고, 직접 도구 결과를 정리한 것이다. 일부 오류의 시작은 전날 설치 기록에 있다. 연구 작성자가 모든 연결 시험을 재실행한 결과가 아니다. 실험 원문 전체의 공개 영구 링크와 해시 고정 evidence 묶음은 아직 없다. 초기 인계 대화 링크를 현재 실험 전체의 원문 링크처럼 사용하지 않는다.

| 사건 | 관측 결과 | 해석 범위 |
|---|---|---|
| Windows Companion의 native Gateway setup | package 설치 뒤 profile 준비에서 Device Guard 관련 실패 | 특정 helper 차단. 파일의 악성 여부나 서명 상태는 확정하지 않음 |
| Windows CLI 설치 | Node MSI 실패 후 사용자 portable Node 26.13.1, OpenClaw 2026.11.3 설치 | 보안 설정 전체를 해제하지 않고 별도 CLI 경로 사용 |
| 모델 인증 | ChatGPT token sharing 인증과 실제 응답 확인 | 모델 호출 권한. 현재 대화 원문·연결 앱 접근권한과 다름 |
| Gateway·UI | loopback 127.0.0.1:18789, health 성공, UI 응답 | 당시 로컬 연결 정상. 상시 서비스와 재부팅 복구는 별도 |
| Claude 메모리 | 12개 가져오기 보고 | 내용 정확성·최신성·승인 유효성은 별도 검토 |
| RELAY-001 | 같은 main으로 sessions_send하여 자기 세션 전송 거부 | 대상 주소 지정 오류를 확인. 제품 전체 실패가 아님 |
| RELAY-002 | Claude MCP에서 별도 dashboard 세션에 전송, ACK와 UI 기록 확인 | Claude → OpenClaw 전달·응답 경로 확인 |
| acpx 설치 | 600000ms timeout 후 list에서 enabled 확인 | timeout을 실패로 단정하거나 무조건 재전송하지 않고 결과 조회 |
| 재로딩 지연 | 약 181초 main-thread 정지, lease 대기, 이후 health 회복 | 장애 이력 유지. 원인 전부가 해결됐다는 증거는 아님 |
| RELAY-003·004 | claude persistent ACP 생성, 명시적 steer와 ACK | OpenClaw → 새 Claude 실행 세션의 요청·응답 확인 |
| RELAY-005 | 현재 desktop 대화에서 기존 ACP key로 직접 agent RPC, ACK, durationMs 4423 | 수동 복사 없는 직접 호출 확인. 모든 ChatGPT 환경의 영구 연결은 아님 |

RELAY-005는 `createSessionIfMissing=false`와 고정 idempotency key를 사용했다. 기존 세션을 대상으로 했고 새 프로젝트 작업을 요청하지 않았다. ACK를 요구한 문장은 도구 사용을 금지했지만, **자연어 금지 문구는 도구 권한이 실제 제거됐다는 증거가 아니다.** ACK 시험들은 독립적인 전체 작업 표본이 아니라 하나의 연결을 단계적으로 점검한 상관된 시험이다.

`attach`, Claude ACP, 원래 MoneyLab Claude 세션은 서로 다른 경로다. attach는 특정 Gateway 세션에 제한된 MCP grant를 가진 Claude 실행을 연결한다. ACP는 OpenClaw가 외부 coding harness를 실행하는 경로다. 터미널의 `openclaw acp`는 Gateway를 외부 ACP client에 제공하는 반대 방향 bridge다. 제품명과 로그인 선택이 같다고 이 경로들을 동일시하지 않는다. ([Attach](https://docs.openclaw.ai/cli/attach), [ACP agents](https://docs.openclaw.ai/tools/acp-agents))

현재 대화의 직접 호출은 desktop의 로컬 실행 도구와 허용을 사용했다. OpenClaw 전용 connector가 이 대화에 영구 설치된 것으로 확인된 것은 아니다. 세션 종료·권한 변화·다른 기기·일반 ChatGPT 웹 화면에서도 같은 접근이 유지되는지는 미검증이다. OAuth의 모델 사용 권한을 현재 ChatGPT 대화 전체의 자동 공유로 설명하지 않는다. ([Gateway query](https://docs.openclaw.ai/cli/gateway/query))

### 원본 토큰과 제품 집계를 대조한다

Claude 원본 JSONL의 assistant message ID가 같은 항목을 중복 제거해 합산했다. 모델 표기는 `claude-opus-5-5`였다. 다음 값은 해당 파일과 조회 시점의 사용 기록이다. 실제 청구액이나 구독 한도 소진율이 아니다. 일반 입력·캐시 생성·캐시 읽기를 같은 단가로 합산하지 않는다.

| 기록 | 응답 수 | 일반 입력 | 캐시 생성 | 캐시 읽기 | 출력 |
|---|---:|---:|---:|---:|---:|
| Claude 터미널 시험 | 8 | 22 | 75,855 | 520,237 | 1,560 |
| Claude ACP 시험 | 3 | 10 | 16,644 | 64,080 | 36 |

원본 파일은 접근 통제된 로컬 Claude 세션 기록 JSONL 2개다. 경로와 세션 식별자는 비식별화를 위해 저장소에 싣지 않는다. 파일에는 개인 맥락과 비밀값이 포함될 수 있으므로 원문 전체를 공개 저장소에 복사하지 않는다. 저장소 연구 기록에는 필요한 비식별 집계와 수집 방법을 싣고, 원본은 접근 통제된 위치에서 참조한다.

OpenClaw의 같은 ACP 세션 usage 조회는 응답 2개가 기록된 시점에 totalTokens와 totalCost를 0으로 반환했다. Claude 원본의 응답 3개 집계와 범위·시점이 일치하지 않는다. 미전파, 집계 미지원, 반영 지연, 표시 오류 가운데 어느 원인인지는 확정하지 않았다. 따라서 0을 무료나 한도 소비 없음으로 해석하지 않는다. 이 표에도 현재 ChatGPT 대화와 중간 OpenClaw 모델 사용량은 빠져 있다. **현재 수치로 전체 setup 비용, 성공 작업당 비용, 중계 비용 절감률을 계산하면 안 된다.** ([Usage tracking](https://docs.openclaw.ai/concepts/usage-tracking))

짧은 출력에도 system prompt, 도구·스킬 설명, 이전 대화, 반환 결과가 입력으로 처리된다. 직접 전달은 중간 coordinator의 모델 호출을 줄일 수 있지만 Claude의 고정 맥락과 이 대화 자체의 비용까지 없애지는 않는다. 캐시의 생성·읽기 필드는 분리하고, 모델별 가격·구독 quota·실제 청구를 별도 열로 남긴다. ([Token use](https://docs.openclaw.ai/reference/token-use), [Prompt caching](https://docs.openclaw.ai/reference/prompt-caching))

### guard와 비대화형 승인은 다른 검증이 필요하다

설치 코드에서 ACP 기본값은 `approve-reads`, 비대화형 승인 처리 기본값은 `fail`이었다. Claude 설정 source는 기본적으로 `project`, `local`이며 user 설정은 별도 opt-in 경로다. ACP status는 RELAY-003을 `claude`, persistent, idle, open, default/manual mode, `relay-test` 작업 폴더로 표시했다. 이는 설정과 상태 관측이며 MoneyLab 작업에서 실제 hook이 실행됐다는 동적 증거는 아니다. ([ACP setup](https://docs.openclaw.ai/tools/acp-agents-setup))

기준 MoneyLab의 hook matcher는 `Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit|Read|Grep`다. guard의 해당 집합 밖 도구명은 최종 PASS 경로로 간다. 따라서 `mcp__…file_write` 같은 이름에 기존 guard가 포괄 적용된다고 보장할 수 없다. 이것은 **정적 보호 범위의 공백이며 실제 보호 파일 변경 우회에 성공했다는 결론이 아니다.** Gateway의 권한·경로 제한과 다른 방어 계층도 함께 확인해야 한다. ([기준 settings](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/.claude/settings.json), [기준 guard](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/.claude/hooks/guard.py))

실제 MoneyLab 적용 전에는 `CLAUDE_PROJECT_DIR`, 전용 Python, Git Bash timeout, 프로젝트 hook 로딩과 실패 시 차단을 확인해야 한다. ACP의 비대화형 승인과 OpenClaw exec 승인은 같은 계층이 아니다. 사용자 확인이 필요한 작업이 실패할 때 `approve-all` 또는 `bypassPermissions`로 해결하지 않는다. 필요한 승인 요청을 사용자에게 전달하고, 승인 범위가 맞을 때만 실행하는 경로를 별도 설계한다. 공식 최신 문서의 옵션도 설치 manifest에 없으면 현재 사용 가능하다고 가정하지 않는다.

## 4. 전체 자동화는 승인과 증거가 연결된 상태 전이로 구현한다

### 전 절차를 연결하되 승인 권한을 모델에 이전하지 않는다

아래 구조는 **목표 설계이며 현재 구현 상태가 아니다.** 사용자의 완전 자동화 목표에는 자료 조사와 계획부터 구현·검증·보고·재개까지 모든 반복 절차가 포함된다. 현재 계약이 사용자에게 남긴 결정은 자동화가 대신 만들어 내지 않는다. 향후 개별 승인 빈도를 줄이려면 허용 대상·한도·만료·예외 처리를 먼저 정책과 계약으로 변경한다. 자동화의 범위를 작게 고정하자는 뜻이 아니라, 각 범위를 검증 가능한 권한으로 표현하자는 뜻이다.

| 상태 | 자동화할 처리 | 필요한 근거와 종료 조건 |
|---|---|---|
| INTAKE | 목표·원문·연구·보고를 분류 | 출처와 기준일을 붙인다. 승인 문구를 연구자료에서 추출해 실행권한으로 쓰지 않는다. |
| CONTEXT_READY | 필요한 맥락 묶음을 구성 | 저장소·worktree·branch·HEAD/tree·WO/ERRATA hash를 실제 상태와 대조한다. 불일치 시 중단한다. |
| CONTRACT_PROPOSED | 작업·허용 파일·명령·예산·수락 기준을 초안화 | 기존 계약과 충돌을 표시한다. 초안을 발행된 계약이나 승인으로 표시하지 않는다. |
| AUTHORIZED | 사용자 승인 범위를 확인 | task·gate·대상 SHA·승인자·범위·만료 조건을 검증한다. 없거나 만료되면 대기한다. |
| RUNNING | 고정 executor에 요청 전달 | run ID·attempt·idempotency key·권한 profile·deadline을 연결한다. 예상 밖 ASK·DENY·예산 초과 시 멈춘다. |
| VALIDATING | 필요한 테스트·정적 검사·독립 검토 수행 | 명령·exit code·집계·diff·검증 대상 hash를 확인한다. 실행 안 된 항목은 PASS로 세지 않는다. |
| EVIDENCE_READY | 결과·상태·비용 기록을 수렴 | 접수·완료·실패·미확인을 구분한다. 증거가 없는 결과는 확정하지 않는다. |
| PUBLISH_PENDING | push·PR·CI·merge를 준비 | 현재 계약의 개별 승인과 정확한 head/base를 확인한다. 승인이 없으면 준비 상태에서 멈춘다. |
| POST_MERGE_AUDIT | 병합 결과를 검증 | merge parents/tree·계약·필수 CI의 정확한 대상과 사후 상태를 확인한다. |
| COMPLETE | 완료와 잔여 위험을 보고 | 모든 수락 기준을 충족했는지 판정한다. 완료는 다음 작업 승인을 만들지 않는다. |
| STOPPED / UNKNOWN | 실패·취소·연결 손실을 처리 | 자동 재시도보다 실제 상태를 조회한다. 완료 여부가 불명확한 쓰기 작업은 재전송하지 않는다. |
| RESUME_REVIEW | 중단·재부팅 후 재개 후보를 구성 | 실제 Git·프로세스·원격 상태를 재조회한다. 필요한 새 승인을 확인한 뒤 해당 상태로 전이한다. |

역할은 research reader, contract coordinator, scoped executor, independent reviewer, evidence collector로 구분할 수 있다. 역할마다 모델을 하나씩 상시 띄울 필요는 없다. 같은 모델을 순차 사용하거나 결정론 코드로 처리할 부분은 그렇게 처리한다. single writer로 같은 worktree의 동시 변경을 막고, 검토자는 검토 대상 hash를 고정한다. 도구 결과는 데이터로 받으며 승인 원문이나 정책을 덮어쓰지 않는다. 이 구조는 기존 오케스트레이션 연구의 실효 권한 교집합과 일치한다. ([SRC-011](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/reports/SRC-011_AGENT_ORCHESTRATION.md))

### 상태 저장, 실행 완료, 승인 유효성을 별개로 검증한다

재개용 checkpoint는 저장소 identity, task·계약 hash, worktree·branch·HEAD/tree, 미커밋 변경 hash, gate와 실제 실행 결과, 승인 참조와 만료 조건, run ID·attempt·idempotency key, 비용 누계와 남은 예산을 연결해야 한다. 민감한 토큰·인증정보·원본 개인 대화는 checkpoint에 넣지 않는다. AUTO-02는 이 중 Git 상태 대조의 근거로 재사용하되 실행 ledger나 승인 저장소로 이름을 바꿔 취급하지 않는다.

Gateway가 요청을 접수한 시각과 작업이 완료된 시각을 분리한다. `status=queued`와 반환 delivery 상태를 완료로 취급하지 않는다. timeout 뒤에는 run ID로 조회하고, 같은 작업의 실제 변경이 이미 발생했는지 확인한다. idempotency key는 중복 방지에 도움이 되지만 모든 외부 side effect에 대한 exactly-once 보증은 아니다. commit·push·PR 생성 등은 각각 실제 상태를 조회할 수 있는 완료 증거가 필요하다. 취소는 요청 접수와 프로세스 종료·자식 회수·변경 상태 보존을 구분한다. ([ACP delivery](https://docs.openclaw.ai/tools/acp-agents/delivery))

STOP, 세션 종료 또는 만료로 끝난 BGA는 ACP history와 checkpoint가 복구돼도 되살아나지 않는다. 재개는 실제 상태를 확인하고 다음 작업과 필요한 승인을 다시 정하는 절차다. 사용자의 5시간 한도로 이 연구가 중단된 사례도 장기 작업의 기록·재개 설계에 포함할 수 있지만, 이것이 PC 재부팅·Gateway crash 복구 시험을 대신하지 않는다. ([작업 절차 §14](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/tasks/README.md))

Windows에서는 portable CLI와 MS Store Gateway alias를 구분하고 실행 경로·버전을 고정한다. 수동 Gateway 탭 종료와 background service 종료를 혼동하지 않는다. Windows가 편리하다는 이유만으로 보호 설정을 해제하지 않고, WSL을 쓴다는 이유만으로 기존 Windows venv·경로·guard가 그대로 호환된다고 가정하지 않는다. 재부팅 시에는 실행 위치, 인증·grant 만료, 장기 프로세스, 로그, 미완료 side effect를 다시 확인한다. 이 절차의 실제 시험은 별도 승인 범위다.

### 연결 선택은 필요한 자동화 범위에 맞춘다

| 후보 | 장점 | 비용·권한·운영 부담 | 현재 판단 |
|---|---|---|---|
| 기존 수동 전달 | 새 조정 계층이 적고 사용자 의도가 명시적 | 복사 오류·상태 재설명·사용자 개입이 반복됨 | 비교 기준선으로 유지 |
| 현재 대화 → Gateway RPC → 기존 Claude ACP | 중간 모델 재해석 없이 정확한 세션 지정 가능 | 현재 desktop 도구 권한에 의존. 계측·기록·재개는 별도 구현 | 제한된 전달의 우선 평가 후보 |
| OpenClaw 모델 coordinator → Claude ACP | 장기 조정·분류·복구·다중 작업 routing 후보 | 추가 모델 호출·context·정책·장애 계층이 생김 | 실제 이득을 비교한 뒤 채택 범위 결정 |
| 명시적 grant의 MCP connector | 다른 client에서 Gateway 대화 접근 후보 | 설치·연결·역할 범위·중계 신뢰 경계가 추가됨 | 현재 직접 호출에 필수 아님. 필요 시 별도 평가 |

공식 MCP Relay는 대화 접근을 위한 선택 경로다. 명시적 client grant와 해제 기능이 있지만, 한 대화에만 제한되는 grant로 단정할 수 없고 relay가 내용을 볼 수 있으므로 end-to-end encryption 경로로 표현하면 안 된다. 문서상 승인 대기와 일반 running의 구분에도 제한이 있다. 이 보고서는 connector를 설치하거나 권한을 확대하지 않았다. ([MCP Relay](https://docs.openclaw.ai/plugins/mcp-relay))

현재 권장 구조는 직접 전달을 최소 실행 경로로 두고, 모델이 필요한 계획·검토에만 모델을 쓰는 것이다. 상시 coordinator는 복구·관찰·routing의 실제 이득이 직접 전달보다 큰지 확인한 뒤 추가한다. 이것은 모델 사용 회피가 아니다. 모델을 써야 하는 판단과 기계적으로 전달·대조할 처리를 구분해 품질과 지속성을 함께 높이는 설계다.

## 5. 실제 작업 비교로 채택하고 연구 기록을 승인과 분리한다

### ACK 반복 대신 승인된 실제 업무를 짝지어 비교한다

평가군 A는 수동 복사와 기존 Claude 실행, B는 현재 대화의 직접 Gateway RPC, C는 OpenClaw 모델 coordinator, D는 필요할 때만 명시적 grant의 connector다. 처음부터 네 구성을 모두 구축하지 않는다. A와 B로 시작하고, C 또는 D가 해결할 필요가 관찰됐을 때 추가한다. 같은 종류·규모의 실제 읽기 전용 업무를 짝지어 비교하고, 모델·effort·기준 commit·맥락 묶음·도구·성공 기준·권한·예산을 고정한다. 실행 순서와 캐시·학습 효과도 기록한다. 서로 다른 모델이나 더 넓은 권한을 준 구성을 단순히 더 좋은 전달 구조라고 결론내리지 않는다.

초기 pilot의 5~10개 짝 작업은 실무적 탐색 규모의 제안이며 통계적 유의성을 보장하지 않는다. 관측 편차가 크면 범위를 확대하거나 결론을 보류한다. 같은 과제를 다시 풀며 얻은 기억이 비교군에 유리하지 않도록 독립적이면서 난도가 비슷한 과제를 배정하거나 순서를 교차한다. 정답·완료 상태는 실행자 자기 보고만으로 채점하지 않는다. 외부 벤치마크 점수를 우리 환경의 합격선으로 복사하지 않는다.

| 측정 축 | 남길 원자료 | 판정 방법 |
|---|---|---|
| 완료 품질 | 정답·요구사항별 충족, 실제 결과·hash | 같은 수락 기준과 독립 검토로 비교 |
| 권한 보존 | 예상·실제 도구, 승인 참조, ASK·DENY·범위 이탈 | 승인 없는 side effect를 허용하지 않음 |
| 사용자 부담 | 개입 횟수·유형·분, 복사·재설명·리뷰·복구 | 시간 절감과 새 유지보수 부담을 함께 비교 |
| 지연·안정성 | 경과시간, 오류, 재시도, 취소·복구 시간 | 성공한 빠른 사례만 고르지 않음 |
| 모델 사용 | 모델·버전·effort, 입력·캐시 생성·캐시 읽기·출력 | 호출별 원본과 집계의 누락·중복을 대조 |
| 현금·구독 | 청구액, 잔여 quota 관측값, 구독·API 구분 | 토큰을 임의 산식으로 구독 소진율에 환산하지 않음 |
| 총비용 | 실패·재작업 포함 비용과 성공 작업 수 | 성공 작업당 비용과 사용자 시간을 병렬 제시 |
| 증거 완전성 | 요청·실행·결과·판정의 연결률 | UNKNOWN을 PASS로 처리하지 않음 |

비용은 setup·정상 실행·idle·실패 복구를 구분한다. 현재 health에서 30분 heartbeat가 관찰됐지만 모든 heartbeat가 항상 같은 모델비를 발생시킨다고 단정하지 않는다. 실제 실행·skip·모델 사용 기록을 확인하고, 필요 없이 24시간 모델 polling을 기본으로 삼지 않는다. 검토 없이 heartbeat를 전부 끄는 것도 이번 연구의 결론이 아니다. ([Heartbeat](https://docs.openclaw.ai/gateway/heartbeat))

권장 수락 기준은 사전에 고정할 후보로 남긴다. 승인 없는 side effect와 보호 범위 이탈은 0건이어야 한다. timeout의 결과를 근거 없이 성공으로 표시한 사례도 0건이어야 한다. 검증한 상태·hash·명령·exit code가 각 완료 판정에 연결돼야 한다. 동일 업무의 품질이 기준선보다 악화되지 않아야 한다. 비용과 사용자 개입의 최소 개선폭은 측정 전 사용자가 정해야 하며, 이 문서는 아직 비용 절감률을 약속하지 않는다. 보안과 정상 업무 완료를 함께 측정하는 기준은 AgentDojo와 반복 일관성 평가의 취지를 참고한 MoneyLab 제안이다. ([P07](https://arxiv.org/html/2406.12045v1), [P08](https://arxiv.org/html/2406.13352v3))

### 도입 단계마다 산출물을 남기고 새 정책은 별도 승인한다

| 단계 | 산출물 | 다음 단계 진입 조건 |
|---|---|---|
| 연구 intake | 본 보고서·출처 대장·시험 근거·미검증 목록 | 자료와 실행 승인 구분, 저장소 문서 반영 범위 확정 |
| 정적 통합 검토 | 현재 기준선·설정 source·tool 경로·승인 대기 경로 표 | 빈틈과 필요한 시험을 명시. 자동 권한 확대 없음 |
| 격리된 정책 검증 | 허용·ASK·DENY·만료·예상 밖 tool·timeout 시험 결과 | 실제 guard·승인 전달을 증거로 확인. 실패 시 중단 |
| 읽기 전용 pilot | A/B 결과와 사용량 대조 | 품질·권한·비용·개입 기준 충족 |
| 로컬 구현·검증 자동화 | 승인된 gate 구간의 실행·독립 검토·증거 | 계약된 범위와 budget 안에서 완료. 현재 게시 승인 유지 |
| 복구·상시 운영 | 재시작·중복 요청·연결 손실·취소 reconciliation | 실제 상태 확인, 중복 side effect 방지, 만료 승인 비복원 |
| 확장 판단 | coordinator·connector·게시 정책의 필요성 평가 | 실측 이득과 별도 정책 승인. 거래 실행은 별도 연구·승인 |

격리된 정책 시험도 사용자 승인 없이 실행하지 않는다. 보호 파일을 실제로 손상시키는 시도를 기본 시험으로 삼지 않는다. 안전한 임시 저장소·비밀 없는 자료·관측 가능한 hook 이벤트를 사용하도록 별도 시험 계약을 만든다. 생산 저장소의 `.claude` 변경과 새로운 tool 권한 부여를 연구 문서 저장과 묶지 않는다. 실거래 자금·주문·지갑·개인키는 이 개발 자동화 pilot에 포함하지 않는다.

| 판단 | 대상 | 이유 |
|---|---|---|
| ADOPT_CANDIDATE | 직접 전달·상태조회·증거 연결의 평가 | 실제 연결 근거가 있고 기존 절차의 수동 부담을 줄일 가능성이 있음 |
| ADOPT_CANDIDATE | 비용·개입·신뢰성의 통합 계측 | 기존 비용·도구 평가 연구의 공백을 직접 다룸 |
| NEEDS_MORE_EVIDENCE | MoneyLab guard 호환, 승인 처리, 전체 업무 생산성 | ACK와 정적 설정만으로 입증하지 못함 |
| DEFER | 상시 coordinator·MCP connector·자동 재개 구현 | 필요성과 권한·복구·운영비 검증이 먼저임 |
| REJECT_CANDIDATE | 0 usage를 무료로 해석, 승인 자동 생성, 권한 우회로 편의 확보 | 측정 오류와 현재 승인 경계를 숨김 |
| OUT_OF_SCOPE | 실제 주문·자금 사용·수익성 확정 | 개발 자동화의 연구 성과와 별개 |

**다음 단일 단계는 읽기 전용 통합 검토**다. 현재 원격·worktree 기준선, 이 보고서의 증거 참조, MoneyLab 전용 executor가 읽을 설정과 hook 경로, 승인 대기·실패 처리 경로를 한 표로 확정한다. 결과는 허용된 경로, 미검증 경로, 후속 시험 범위를 구분한 검토안이다. 이 단계는 파일 쓰기·테스트·설정 변경·새 executor 실행을 포함하지 않는다. 이후 연구자료 저장, 격리 정책 시험, 실제 업무 pilot은 각각 구체적 범위를 가진 승인으로 진행한다. 절차를 무한히 늘리려는 것이 아니라, 같은 검토를 매번 대화에서 반복하지 않도록 한 번의 명시적 계약과 기계 판정으로 옮기는 것이 목적이다.

저장소 반영 제안 위치는 `docs/research-intake/2026-11-12/OPENCLAW_AUTOMATION_RESEARCH.md`다. 현재 산출물은 Git 저장소 밖에 있다. 반영 시에는 기존 intake와 같은 비권위 표식을 유지하고, source register와 비식별 evidence 참조를 연결한다. 운영 중인 세션 ID·로컬 개인 경로·callback 인증 URL·토큰은 공개 문서에 불필요하게 싣지 않는다. 기존 연구를 덮어쓰지 않고 신규 연구의 결정과 적용 범위를 별도 기록한다. ([기존 intake 경계](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06/README.md))

### 연구 결론

OpenClaw의 가치는 모델을 하나 더 호출하는 데 있지 않고, 현재 사람 사이에 끊겨 있는 절차를 관측 가능한 상태 전이로 연결하는 데 있다. 직접 전달은 그 연결의 실현 가능성을 보여 줬다. 다음 투자는 ACK를 더 얻는 데 쓰기보다 실제 업무 완료, 승인 보존, 비용 수집, 복구의 빈틈을 검증하는 데 쓰는 것이 타당하다.

MoneyLab이 채택해야 할 것은 제품 전체에 대한 일괄 신뢰가 아니라 검증된 자동화 범위다. 그 범위가 확대되면 사용자는 반복 전달과 상태 추적에서 벗어나 목표·예산·위험·권한 정책을 결정하는 데 집중할 수 있다. 최종 순수익 판단은 여전히 전략과 데이터의 독립 검증, 거래비용, 반복 운영비, 실제 운영 증거에 달려 있다.

## 부록 A. 출처 대장과 읽은 범위

아래 날짜는 연구 기준일 이전의 제출·수정 또는 출판 정보다. 원문 전체를 모두 재현한 것은 아니며, 읽은 범위를 명시했다. 웹 자료의 조회 기준은 2026-11-12다. 공식 문서는 제품 변경에 따라 달라질 수 있으므로 설치 2026.11.3 코드의 확인 범위를 우선한다.

| ID | 고정 식별자·상태 | 읽은 범위와 제한 |
|---|---|---|
| P01 | [2604.03131v1](https://arxiv.org/abs/2604.03131v1), preprint | metadata와 HTML 평가 설계·결과·방어 제안. 게재 미확인 |
| P02 | [2602.08412v2](https://arxiv.org/abs/2602.08412v2), preprint | metadata와 HTML 시나리오·실행·결과 |
| P03 | [Google Research 출판 기록](https://research.google/pubs/openclaw-in-the-wild-security-analysis-of-autonomous-agents/), 학술지 게재 표기 | 기관 초록·서지. [IEEE 본문](https://ieeexplore.ieee.org/abstract/document/11595140)은 418 오류로 미열람 |
| P04 | [2606.12344v2](https://arxiv.org/abs/2606.12344v2), preprint | HTML 본문·비용 부록. v1 수치와 혼합하지 않음 |
| P05 | [2605.10912v1](https://arxiv.org/abs/2605.10912v1), preprint | HTML 방법·결과·한계 |
| P06 | [2407.01502v1](https://arxiv.org/abs/2407.01502v1), 인용 판본은 preprint | 초록·HTML 비용·평가·holdout 논의 |
| P07 | [2406.12045v1](https://arxiv.org/abs/2406.12045v1), 인용 판본은 preprint | 초록·HTML 방법·사례 |
| P08 | [2406.13352v3](https://arxiv.org/abs/2406.13352v3), 인용 판본은 arXiv | 초록·HTML 평가·방어. 이 판본을 넘는 출판 상태 주장 없음 |
| P09 | [TACL 2024.tacl-1.9](https://aclanthology.org/2024.tacl-1.9/), 동료심사 학술지 | 출판 초록·서지정보. 현재 모델 성능으로 확대하지 않음 |
| D01 | [Attach](https://docs.openclaw.ai/cli/attach), 공식 문서 | 임시 MCP 연결과 grant의 범위 |
| D02 | [ACP agents](https://docs.openclaw.ai/tools/acp-agents), [sessions](https://docs.openclaw.ai/tools/acp-agents/sessions), [delivery](https://docs.openclaw.ai/tools/acp-agents/delivery) | 외부 harness·지속 세션·bind·재개·접수와 완료의 구분 |
| D03 | [ACP setup](https://docs.openclaw.ai/tools/acp-agents-setup), 공식 문서 | 권한 기본값·비대화형 제약. 설치 manifest와 다른 옵션은 적용 주장 제외 |
| D04 | [MCP Relay](https://docs.openclaw.ai/plugins/mcp-relay), 공식 문서 | connector·grant·중계 신뢰 경계. 실제 설치·활성화하지 않음 |
| D05 | [Gateway query](https://docs.openclaw.ai/cli/gateway/query), 공식 문서 | 로컬 RPC 경로. 현재 desktop 권한 범위와 구분 |
| D06 | [Token use](https://docs.openclaw.ai/reference/token-use), [Prompt caching](https://docs.openclaw.ai/reference/prompt-caching), [Usage tracking](https://docs.openclaw.ai/concepts/usage-tracking) | 맥락·캐시·부분 집계·quota와 비용 구분 |
| D07 | [Security](https://docs.openclaw.ai/gateway/security), [Heartbeat](https://docs.openclaw.ai/gateway/heartbeat) | Gateway 신뢰 경계와 주기 실행 연구 범위 |
| R01 | [기존 연구 묶음](https://github.com/swk3169/MoneyLab/tree/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/research-intake/2026-11-06) | 통합 결론과 SRC-004·005·008·009·011을 고정 객체에서 읽음 |
| R02 | [작업 계약 묶음](https://github.com/swk3169/MoneyLab/tree/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/tasks) | AUTO-01과 ERRATA, AUTO-02와 ERRATA-003, GOV-AUTOMATION-02, README 읽음 |
| R03 | [Supervisor 계약](https://github.com/swk3169/MoneyLab/blob/8eed531cd09ff2748bf91165abd0e1a69b8148c8/docs/supervisor_proposal_contract.md) | 제안·계약·승인 경계 |
| L01 | 설치 OpenClaw 2026.11.3·acpx 0.19.4의 schema·config·Claude adapter | 읽기 전용 코드 조회. 다른 버전·실제 hook 호출을 입증하지 않음 |
| L02 | Claude 원본 JSONL 2개와 OpenClaw usage 결과 | 응답 ID 중복 제거 집계. 누락 없는 전체 비용 또는 청구액 아님 |
| S01 | 현재 대화의 설치·연결·장애 화면과 직접 도구 결과 | 비공개 세션 증거. 공개 영구 원문·redacted manifest·hash 고정은 미완료 |

## 부록 B. 새 세션 인계에 필요한 최소 상태

이 보고서는 저장소 밖 연구 산출물이며, 저장소 반영·설정 변경·실행 승인으로 사용하지 않는다. Git 비교 기준은 `8eed531…`이고 현재 원격 최신 여부는 다시 조회해야 한다. AUTO-02는 완료 이력으로 유지하되 새 자동 재개·ledger 구현으로 표현하지 않는다. 기존 연결 시험은 반복하지 않고 필요한 경우 상태조회로 확인한다. 시험 결과는 당시 관측이며 현재 프로세스·grant 생존을 보장하지 않는다.

직접 Gateway → 기존 Claude ACP 호출은 성공했다. 일반 ChatGPT 웹에서의 동일 접근, 영구 connector, 상시 coordinator는 미검증이다. 원본 Claude 토큰과 OpenClaw ACP 0 집계는 불일치한다. 비용·구독 quota는 추가 대조가 필요하다. guard의 MCP 도구명 검사 범위와 실제 승인 전달도 미검증이다. 다음 단계는 읽기 전용 통합 검토이며, 구현이나 쓰기 시험을 자동으로 시작하지 않는다.
