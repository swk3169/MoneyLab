AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-12
STATUS: DESIGN_REPORT_RECEIVED_NOT_APPROVED
CASE_STUDY_STATUS: PARTIAL
INTAKE_EDIT_HISTORY: SOURCE_REGISTER.md의 편집 이력 참조. 위 STATUS는 사례 기록 작성 시점의 문서 상태이며 CASE_STUDY_STATUS와 다르다.

# 연구자료 반영 자동화 시범 작업

## 목적

ChatGPT가 조사하고 검토한 연구자료를 Claude Code에 직접 전달한다. Claude가 저장소 규칙에 맞는 문서 반영안을 작성하고, ChatGPT가 독립 검토한다. 사용자가 승인한 범위만 저장소에 반영한다. Git 게시와 병합은 현행 승인 경계를 따른다.

이 사례는 최종 목표인 거래비용과 운영비 차감 후 순수익을 위한 개발 자동화 연구다. 토큰 사용 회피 자체를 목표로 삼지 않는다. 품질, 비용, 사용자 개입, 재작업, 권한 보존을 함께 평가한다.

## 입력과 제안 산출물

- 입력: MoneyLab OpenClaw 자동화 통합 연구 보고서. 저장소 밖에서 작성한 비권위 연구자료.
- 저장소 비교 기준: 8eed531cd09ff2748bf91165abd0e1a69b8148c8. 현재 원격 최신 여부는 미검증.
- 현지 checkout C:/MoneyLab은 09504cd 계열의 오래된 상태다. 최신 프로젝트 상태로 취급하지 않는다.
- 제안 파일: docs/research-intake/2026-11-12/OPENCLAW_AUTOMATION_RESEARCH.md.
- 제안 파일: docs/research-intake/2026-11-12/SOURCE_REGISTER.md.
- 제안 파일: docs/research-intake/2026-11-12/AUTOMATION_CASE_STUDY.md.
- 필요한 색인 변경은 별도 허용 목록에 포함해야 한다. 기존 연구를 덮어쓰지 않는다.

## 전달한 실행 범위

TASK_ID는 OPENCLAW-INTAKE-01이다. DESIGN_INVESTIGATION 읽기 전용 조사와 계약 초안만 요청했다. 기존 Claude ACP 시험 세션을 대상으로 직접 Gateway agent 요청을 사용했다. createSessionIfMissing은 false로 지정했다. 고정 idempotency key로 중복 전송을 방지했다.

모델 호출은 Claude 조사 요청 1회다. 중간 OpenClaw 모델의 재해석 요청은 하지 않았다. 전체 과정의 토큰과 실제 비용은 아직 집계하지 않았다.

파일 생성, scratchpad, 설정 변경, 설치, 테스트, 새 worktree, stage, commit, push, PR, merge, 다른 세션 전송을 금지했다. 과거 승인이나 연구 문장을 새 실행 승인으로 사용하지 않도록 명시했다. 최신 원격 기준선은 미검증 placeholder로 남기도록 요청했다.

## 관측한 실행 이력

1. ChatGPT가 완성된 연구보고서와 고정 기준의 작업 규칙을 입력으로 지정했다.
2. ChatGPT가 직접 Gateway 요청을 보냈다. 같은 요청은 재전송하지 않았다.
3. 로컬 CLI 호출은 출력 없이 exit 1로 종료됐다. 원인은 이 결과만으로 확정하지 않았다.
4. 동일 run ID의 agent.wait 조회는 timeout을 반환했다. 이를 작업 자체의 실패나 취소로 해석하지 않았다.
5. Claude 원본 기록에서 연구보고서 Read 호출과 본문 반환을 확인했다.
6. Claude가 고정 Git 객체의 tasks README, TEMPLATE, CLAUDE.md, 기존 research intake README를 조회하는 Bash 호출을 요청한 것을 확인했다.
7. 초기 상태 조회 시점에는 Git 조회 결과와 최종 계약 초안이 반환되지 않았다. Gateway sessions.list는 해당 ACP 세션을 running, hasActiveRun=true로 반환했다.
8. 이후 Gateway 터미널에서 TEMPLATE.md와 CLAUDE.md의 git show 읽기 승인 요청이 관측됐다. 사용자가 승인한 뒤 작업이 진행됐다. 앱 승인 화면이 아니라 터미널 입력을 요구한 점은 사용자 개입으로 기록한다.
9. 사용자가 Claude의 DESIGN_INVESTIGATION 최종 보고서를 전달했다. Claude는 연구보고서, CLAUDE.md, TEMPLATE.md, 기존 intake README를 읽었다고 보고했다. docs/tasks/README.md는 권한 거절로 읽지 못했고 재시도하지 않았다고 보고했다. 권한 거절의 원인은 확정하지 않았다.
10. ChatGPT가 보고서를 읽고 독립 검토를 시작했다. 계약은 조건부 값과 누락 항목이 있는 DRAFT이며 발행하거나 승인하지 않았다.
11. ChatGPT가 연결된 GitHub 조회로 원격 main SHA 8eed531cd09ff2748bf91165abd0e1a69b8148c8와 tree 8d515890e0767b9b70d809325c69ec4ea492b442를 재확인했다. C:/MoneyLab checkout에는 기존 변경이 있어 쓰기 대상으로 사용하지 않았다. AUTO-02 source 작업공간은 읽기 전용 조회에서 clean이었다.
12. 계약 정정 요청의 로컬 전달 과정에서 명령 실행기 오류와 JSON 형식 오류가 발생했다. 파일 존재와 원본 기록을 읽어 접수 여부를 확인했다. 이후 설치된 Node 실행기에 JSON을 직접 전달했다. 같은 idempotency key를 유지했고, 전달 경로 오류를 모델 작업 실패로 표시하지 않았다.
13. 직접 호출의 응답은 60초 timeout이었다. 그러나 Claude 원본 기록에는 정정 답변이 완료돼 있었다. ChatGPT가 이 답변을 읽어 결과를 회수했다. timeout과 실제 작업 완료를 분리하고 무조건 재전송하지 않은 사례다.
14. 정정 답변은 도구 없이 문안만 작성했다고 보고했다. 최종 계약은 아직 미승인이다. 생성 전 존재 검사와 생성 후 identity 검증의 구분, 문서 상태와 사례 상태의 구분, 필수 CI 실패와 experimental 실패의 구분, 필수 수락 기준의 계약 본문 포함을 추가 검토했다.

## 현재 판정

- 연구자료 자동 전달과 Claude의 실제 Read 수행: 확인.
- 저장소 규칙 읽기: 일부 완료라는 Claude 보고와 README 읽기 거절 보고가 있다. 거절된 문서는 Claude가 읽은 것으로 표시하지 않는다.
- 작업 계약 초안: 수신 완료. 최종 계약으로 채택하지 않았다.
- ChatGPT 독립 검토: 진행 중. 원문 무수정 보존과 비식별화 충돌, 사실 기록과 승인 주장 구분, 불완전한 계약 필드 등을 검토한다.
- 저장소 연구 파일 작성, 검증, commit, push, PR, merge: 미수행.
- 자동화 전체 성공: 판정하지 않음.
- 대기 원인: 터미널 승인 대기가 실제로 관측됐다. 동시 Gateway 연결 지연과 이 승인 대기가 모든 정체의 단일 원인인지는 미확인이다.

ACK 수신과 실제 파일·Git 도구 작업은 다른 시험이다. 이번 사례는 도구 사용이 포함된 읽기 전용 작업에서도 접수, 실행, 완료를 구분해야 함을 보여 준다. timeout 뒤에 결과를 조회한 이력도 자동화 연구의 일부다.

## 다음 경계

Claude 초안을 ChatGPT가 검토하고 미해결 계약 조항을 정리한다. 거절된 호출은 자동 재시도하지 않는다. 다음 단계에서 필요한 읽기 범위와 저장소 변경에 필요한 최종 계약을 구분한다. Work Order 발행, 파일 작성, Git 게시를 수행한 것으로 표시하지 않는다.

원본 대화, 인증 URL, 토큰, 불필요한 개인 경로와 내부 세션 ID는 공개 저장소에 복사하지 않는다. 이 기록의 저장소 반영도 별도 문서 작업 범위다.

## 사례 상태

- CASE_STUDY_STATUS: PARTIAL
- 지시 전달과 Claude 측 작업 완료는 기록으로 확인됐지만, 정상 응답 경로 회수는 실패했다.
- 전체 절차 자동화와 비용 절감은 입증되지 않았다.

## 추가 보고: 마지막 수정 지시 전달

출처: 사용자가 전달한 ChatGPT 보고. Claude가 재확인하지 않았다.

- 마지막 수정 지시는 OpenClaw를 통해 1회 전달됐다.
- 호출은 60초 timeout으로 끝났다.
- 이후 ChatGPT가 Claude 세션 기록에서 지시 수신과 수정안 생성 완료를 확인했다.
- 정상 응답 경로의 회수는 실패했고, 기록에서 결과를 복구했다.
- 전체 절차 자동화와 비용 절감은 입증되지 않았다.
- 사용자는 시간과 토큰 소모 때문에 추가 시험을 중단하기로 했다.

## timeout 사건의 동일성

- 사례 기록 13항의 60초 timeout과 위 추가 보고의 60초 timeout이 같은 사건인지는 미확인이다.
- 두 보고는 출처별로 따로 적는다. 별개 사건으로 세지 않고, timeout 건수를 합산하지 않는다.

## 보존 시점 상태

- 사례 기록의 "현재 판정"과 "다음 경계"는 그 기록을 작성한 시점의 상태다.
- 이 문서는 비권위 연구 참고자료다. 승인, 실행 권한, 채택 결정이 아니다.
- 이번 보존 작업에서는 OpenClaw 추가 시험과 모델 호출을 하지 않았다.
