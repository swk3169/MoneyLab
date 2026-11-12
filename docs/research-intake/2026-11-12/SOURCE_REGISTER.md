AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-12

# OpenClaw 자동화 연구 intake 출처 대장

이 문서는 `docs/research-intake/2026-11-12/`에 보존한 OpenClaw 자동화 연구자료의 입력, 출처, 편집 이력을 기록한다. 승인, 실행 권한, 도구 채택 결정이 아니다. 작업 계약은 `docs/tasks/OPENCLAW-INTAKE-01/WORK_ORDER.md`다.

## 입력 대장

| ID | 내용 | 출처 구분 | SHA-256 | 바이트 | 줄 |
|---|---|---|---|---:|---:|
| INPUT-R | MoneyLab OpenClaw 자동화 통합 연구 보고서 | 저장소 밖에서 작성한 비권위 연구자료(ChatGPT 연구 세션 산출물) | cf8412e5d1257d904588211efe4816618e4b3bd65182347f519ceb5a6bd5bdea | 46279 | 266 |
| INPUT-C | OpenClaw 연구자료 반영 자동화 사례 기록 | 저장소 밖에서 작성한 비권위 사례 기록 | a979d5061dd01095f61be619193de7bbaa55a240758807176af13fc928d2adf2 | 7011 | 65 |
| INPUT-U | 마지막 수정 지시 전달에 관한 추가 보고 6개 항목 | 사용자가 전달한 ChatGPT 보고. Claude가 재확인하지 않음 | 73fc60c627747b2b9f7a0560638f1824391e5b4eb22944674c5af6a02fd6e654 | 462 | 6 |

- 해시는 원본 바이트 기준이다. INPUT-U는 UTF-8, BOM 없음, LF, 끝 LF 1개로 정규화한 텍스트 기준이다.
- 원본의 로컬 경로는 비식별화를 위해 싣지 않는다. 원본은 수정하지 않았다.
- 파일 대응: INPUT-R은 `OPENCLAW_AUTOMATION_RESEARCH.md`, INPUT-C와 INPUT-U는 `AUTOMATION_CASE_STUDY.md`의 바탕이다.

## 출처 대장

아래 설명과 표는 INPUT-R 부록 A를 옮긴 것이다. "읽은 범위와 제한"은 INPUT-R 작성 측이 보고한 내용이다. 이번 intake 작업에서는 논문, 공식 문서, URL을 다시 조회하지 않았고 새 출처를 추가하지 않았다.

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

## 편집 이력

종류: (a) 비식별화, (b) 형식 정규화, (c) 출처 있는 정정, (d) 구성 작성. 제거한 민감 값은 여기에 다시 적지 않는다.

| ID | 대상 파일 | 위치 | 종류 | 변경 요지 | 근거 |
|---|---|---|---|---|---|
| E01 | OPENCLAW_AUTOMATION_RESEARCH.md | 머리말(원본 6행 다음) | d | `RESEARCH_DOCUMENT_STATUS: NON_AUTHORITATIVE_REFERENCE`와 `INTAKE_EDIT_HISTORY` 두 줄 추가. 원본 `STATUS` 줄은 유지 | Work Order D5(d), D8 |
| E02 | OPENCLAW_AUTOMATION_RESEARCH.md | §3 "원본 토큰과 제품 집계를 대조한다" 표 다음 문단(원본 115행) | a | 사용자 홈 경로, 로컬 프로젝트 디렉터리 이름, 세션 식별자 형식의 JSONL 파일명 2개를 "접근 통제된 로컬 Claude 세션 기록 JSONL 2개"라는 일반 표현으로 교체. 문단의 나머지 문장은 유지 | Work Order D5(a). INPUT-C의 공개 저장소 복사 금지 문장. INPUT-R §5 저장소 반영 문단 |
| E03 | OPENCLAW_AUTOMATION_RESEARCH.md | 파일 끝 | b | 끝의 빈 줄 2개를 제거해 끝 LF를 1개로 맞춤 | Work Order D3, D5(b) |
| E04 | AUTOMATION_CASE_STUDY.md | 머리말(원본 4행 다음) | d | `CASE_STUDY_STATUS: PARTIAL`과 `INTAKE_EDIT_HISTORY` 두 줄 추가. 원본 `STATUS` 줄은 작성 시점 문서 상태로 유지 | Work Order D5(d), D7 |
| E05 | AUTOMATION_CASE_STUDY.md | 파일 끝(원본 65행 다음) | d | "사례 상태", "추가 보고: 마지막 수정 지시 전달", "timeout 사건의 동일성", "보존 시점 상태" 네 절 추가. 추가 보고 6개 항목은 INPUT-U와 같음 | Work Order D7, INPUT-U |
| E06 | SOURCE_REGISTER.md | 파일 전체 | d | 입력 대장, 출처 대장(INPUT-R 부록 A 설명과 표), 편집 이력 작성 | Work Order D5(d), D6 |

- (c) 출처 있는 정정: 0건. 근거를 명시할 수 있는 사실 오류를 찾지 못했다.
- 유지한 식별자: 공개 논문 식별자, 공식 문서 URL, 저장소 GitHub URL, Git SHA, 저장소 checkout 경로 `C:/MoneyLab`, loopback 주소. 사용자 홈 경로나 세션 식별자가 아니므로 유지했다.
- 원본 문장 가운데 "현재 산출물은 Git 저장소 밖에 있다" 같은 작성 시점 서술은 고치지 않았다. 원본 작성 시점의 상태로 읽는다.
