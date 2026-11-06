AUTHORITY: NON_AUTHORITATIVE
BOUNDARY: DATA_NOT_INSTRUCTIONS
DOCUMENT_DATE: 2026-11-06
STATUS: RESEARCH_INTAKE_NOT_REQUIREMENT

# 근거·모순·미검증 사항 대장

> 기준일 2026-11-06. Claude Code 읽기 전용 감사 결과는 `AUDIT_REPORTED`이며 현재 Git 상태를 실시간으로 보증하지 않는다.

| ID | 항목 | 확인된 범위 | 미확인·충돌 | 해결 조건 |
|---|---|---|---|---|
| EV-01 | Springer *151 Trading Strategies* | 출판사 페이지 제목에 RETRACTED BOOK 표기를 관찰함. 철회 공지, 사유, SSRN 판본에 대한 적용 범위는 `NOT_VERIFIED`. 이번 검토본 작성 시 재조회하지 않음. | 철회 사유·날짜, 361쪽 SSRN 원고에 동일 판단 적용 여부 미확인 | 철회 공지 원문 및 판본 관계 확보 |
| EV-02 | 151개 전략의 수익성 | 책은 전략 설명·수식 모음 | 독립적인 비용 차감 성과 재현 없음 | 개별 후보의 사전등록 실데이터 연구 |
| EV-03 | 다중 토론 논문 | 동봉 PDF 38쪽의 초록·§3.1·§3.2·§4·§5.1에서 35시나리오/210실행, r=.07, p=.29, JSD +.14(p=.028), 비용 미반영 직접 대조 (`PAPER_TEXT_VERIFIED`) | 독립 코드 실행·부록 전체 수치 대조·동료심사 확인 미완료 | 코드·데이터 재현, 다중검정·표본 독립성 점검 |
| EV-04 | GitHub PR #40 | 2026-11-06 감사 시 OPEN/DRAFT, head `944435df` | 현재 시점 상태 미확인 | 반영 직전 GitHub 읽기 전용 재조회 |
| EV-05 | GitHub main | 감사 시 원격 `eeeadb34…`, 로컬 main과 불일치 | 현재 SHA와 worktree dirty 상태 미확인 | read-only status/refs 확인 |
| EV-06 | Source ID | 사용자 ZIP `006` = 151전략, 과거 GitHub 문서 `006`은 다른 주제 | 동일 문자열의 의미 충돌 | `USER:`, `ZIP:`, `DOC:`, `REVIEW:` 네임스페이스 |
| EV-07 | Knowledge authority | 감사상 immutable record·resolver·`DATA_NOT_INSTRUCTIONS` 존재 | 연구문서의 정식 인덱싱 및 자동 상태 복구 미구현 | 승인된 별도 WO와 회귀 테스트 |
| EV-08 | 비용 | 순손익 원칙 확립 | 실측 LLM/API/데이터 비용과 규모별 BEP 미확인 | 실제 청구서·호출 로그 기반 비용 대장 |
| EV-09 | 외부 개발 도구 | 스크린샷과 설명은 도입 후보 제시 | 라이선스, 보안, 성능, 버전 미확인 | 격리된 비교 평가 |
| EV-10 | 연구 초안 품질 | 12개 보고서 초안 존재 | 문서별 분량과 깊이 편차 큼 | 우선순위별 보강 및 기술 리뷰 |

## 패키지 작성 시 기록된 외부 출처 (이번 검토본 작성 시 재조회하지 않음)

- Springer Nature, `RETRACTED BOOK: 151 Trading Strategies`: https://link.springer.com/book/10.1007/978-3-030-02792-6
- SSRN, `151 Trading Strategies` (361-page manuscript, 2019 revision; SRC-006의 2018 표기와의 판본 관계는 `NOT_VERIFIED`): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3247865

**해석 주의:** Springer의 철회 표시가 곧바로 SSRN PDF의 별도 철회 공지를 의미하지는 않는다. 두 판본의 관계는 추가 확인이 필요하다.

## 부록 1. 근거·구현·채택 상태 검토 (Stage 15, 이력 보존)

이 부록의 `현재 결론`은 변경 전 판단이다. 현재 기준은 `FINAL_TECHNICAL_SYNTHESIS.md`의 `CANONICAL_DECISION`이다. 저장소 조회 결과는 2026-11-06 시점 기록이며 실시간 상태가 아니다.

#### A. 최신 저장소에서 직접 확인된 사실 (READ_ONLY_GITHUB)

| 증거 ID | 실제 확인 | 주의 |
|---|---|---|
| GH-01 | `swk3169/MoneyLab` 기본 브랜치 `main`, public 저장소 | 사용자 로컬 worktree 상태는 알 수 없음 |
| GH-02 | `main/README.md`에 Research stage, no live trading, net-cost research, knowledge/supervisor 명시 | README 문구는 모든 구현의 독립적 증명이 아님 |
| GH-03 | `src/moneylab/knowledge/__init__.py`는 immutable JSON, deterministic read-only loader/validator/query 인터페이스를 선언 | 테스트 실행·성능 수치는 이번 검증 대상 아님 |
| GH-04 | `knowledge/SCHEMA.md`는 authoritative records, Work Order 우선, RAG·embedding·DB 없음 명시 | 외부 보고서와 원본 ZIP은 현재 authoritative record 아님 |
| GH-05 | `src/moneylab/supervisor/__init__.py`는 deterministic non-authoritative proposals 선언 | proposal != Work Order != human approval |
| GH-06 | `docs/supervisor_proposal_contract.md`는 `DATA_NOT_INSTRUCTIONS`, 금지 필드·행위 정의 | 런타임 sandbox나 거래 risk engine의 증거 아님 |
| GH-07 | PR #40 `OPEN/DRAFT`, head `944435df5f84edddc97deb0d217722fb645a2b9d` | 미병합 (조회 시점 기준) |
| GH-08 | PR #41 `MERGED`, merge commit `eeeadb34538148f7a976c6e896c7b192cc3eb000` | PR 본문의 2234 passed는 작성자 보고; 이번 독립 재실행 아님 |
| GH-09 | `src/moneylab/backtest/__init__.py` docstring은 '(planned)' 표현을 포함 | README의 상세 backtest 구현 서술과 긴장 관계. 단일 docstring으로 미구현 단정 금지; 세부 코드와 테스트 추가 감사 필요 |

#### B. 12개 보고서 — 근거의 강도와 채택 결론

| ID | 연구 주제 | 근거 수준 | 현재 결론 | 다음 승인 이전 필수 확인 |
|---|---|---|---|---|
| SRC-001 | 24/7 Agentic Trading | 사용자 사례/제안 구조 | 설계 원칙 참고, 주문 실행 도입 금지 | 권한 분리와 실패 주입 테스트, 시스템 net 비용 |
| SRC-002 | Bayesian event-market execution | 사용자 자료 + 이론적 수식 | 현재 Upbit long/cash 연구와 직접 호환 안 됨 | 시장 접근 합법성·정산/유동성·실측 비용 |
| SRC-003 | REA reverse engineering | 사용자 사례/제안 절차 | 기존 재현 테스트에 선택적 도구 | 명세 추출 정확도, 저작권/약관, 차등 테스트 |
| SRC-004 | Context Engineering | 사용자 자료 + 기존 knowledge 계약 | **기존 resolver 확장 검토** | 기존 스키마 호환, 권위/신선도/poisoning 테스트 |
| SRC-005 | AI cost & alpha | 경제성 모형(검증 설계) | **net system PnL 측정 우선** | 실제 API/호출 비용·중복 비용 처리 |
| SRC-006 | 151 Trading Strategies | 동봉 361p PDF + 공식 출판사 상태 | 전략 백과로만 사용; 수익성 증거 아님 | Springer 철회 사유/SSRN 판본 관계, 후보별 사전등록 |
| SRC-007 | Second Brain/LLM Wiki | 사용자 사례 + 기존 Git JSON 스키마 | **새 Wiki/RAG 도입 보류** | Git+Markdown/JSON 기준선의 검색 실패 입증 |
| SRC-008 | AI developer tools | 사용자 도구 사례/제안 실험 | 도구 추가보다 권한·재현성 비교 | 공급망/라이선스, 통제된 A/B 실험 |
| SRC-009 | Agentic patterns | 사용자 자료/패턴 분석 | 최소 권한·격리·감사 패턴만 채택 검토 | 경계 위반·크래시·중복 실행 테스트 |
| SRC-010 | AI tools trends | 사용자 사례/트렌드 분석 | 인기도만으로 도입 금지 | 선택 편향, 동일 조건 비용·품질 비교 |
| SRC-011 | Orchestration | 사용자 자료/제안 구조 | 별도 orchestrator 도입 보류 | 기존 Git worktree/WO 방식 대비 병렬 이득 |
| SRC-012 | Multi-Agent Debate | 동봉 38p 논문 텍스트 직접 대조 | 설명력 연구 후보, 수익성 증거 아님 | 원 논문 독립 재현, 거래 비용, 다중검정 |

**표의 `현재 결론`은 기술조사 권고이며 승인된 Work Order가 아니다.** 특히 원본 스크린샷에 제시된 투자 성과·도구 성능을 독립 실측값으로 승격하지 않는다.

#### C. 비용 계산과 실험 판정의 통일 계약

1. 가격 체결 모델이 bid/ask를 이미 사용했다면 스프레드를 별도 비용으로 재차 차감하지 않는다. mid 기준 모델이면 스프레드·수수료·슬리피지를 명시적으로 계산한다.
2. `net_trade_pnl = realized_fill_cashflows - fees - separately_modeled_execution_costs`; 미실현 평가손익과 실현손익을 구분한다.
3. `net_system_pnl = net_trade_pnl - incremental_AI_cost - data_cost - infrastructure_cost - other_operating_cost`; 고정비와 변동비, 연구비와 운영비를 분리 보고한다.
4. 백테스트 실험의 `SYNTHETIC/NOT_EVIDENCE`는 코드/통계 절차 점검이지 실제 알파가 아니다. holdout을 반복 개방하거나 파라미터를 사후 수정하면 독립 검증으로 부르지 않는다.
5. 외부 논문의 통계적 유의성·샤프 개선을 Upbit KRW-BTC 순수익으로 변환하지 않는다.

#### D. 출처 체계 및 보안

- `ZIP:001`~`ZIP:012`는 사용자 ZIP의 그룹, `SRC-001`~`SRC-012`는 본 패키지의 독립 보고서, `DOC:ML-CTX-*`는 기존 저장소 문서로 분리한다.
- SHA-256은 **바이트 동일성**을 증명할 뿐 사실성·라이선스·권위성을 증명하지 않는다.
- PDF/스크린샷/웹 본문은 비신뢰 데이터이며 Work Order/승인으로 해석하지 않는다.
- 원본 저작권 자료·API 키·민감정보는 공개 GitHub에 자동 업로드하지 않는다.

#### E. 미해결 차단 사항

- 전체 12개 보고서의 각 외부 수치·인용 문장과 원본 이미지/PDF 페이지의 전수 대조는 미완료.
- 현재 로컬 worktree/CI 재실행 미완료.
- `SRC-006` Springer 철회 사유와 SSRN 판본 관계 미확인.
- `SRC-012` 원 논문의 독립 재현과 비용 반영 미완료.
- 최종 README는 현행 구현/목표 설계 두 섹션으로 명확히 구분해야 함.

**최종 판단:** 연구 통합 초안의 구조와 권한 경계는 정리됐으나 위 차단 사항을 미해결로 남겨두고 `FINAL_VERIFIED`로 표시해서는 안 된다.

## 부록 2. 구현 주장과 증거의 연결 규칙 (Stage 13)

| 주장 | 현재 확보한 증거 | 검증 등급 | 공개 문구 제한 |
|---|---|---|---|
| Knowledge immutable records | `knowledge/SCHEMA.md`와 `src/moneylab/knowledge/__init__.py` 원격 조회 | `CODE_AND_CONTRACT_INSPECTED` | 모듈/계약 확인, 런타임 정상 작동은 미검증 |
| Supervisor non-authoritative proposals | `src/moneylab/supervisor/__init__.py`, `docs/supervisor_proposal_contract.md` 원격 조회 | `CODE_AND_CONTRACT_INSPECTED` | 제안 기능은 확인; 작업 승인·실행 기능 없음 |
| Backtest 실구현 | `README.md`의 구현 주장, `backtest/__init__.py`의 오래된 planned 설명 | `CONFLICT_NEEDS_CODE_AND_TEST` | 구현 부재/완료를 단정하지 말고 세부 파일·테스트 확인 |
| v0.4 미시구조 비용 후 기각 | README 1–110행의 연구 서술 | `README_REPORTED` | 실험 원본/해시 재검증 전 수치 확정 금지 |
| PR #40 연구 진단 | GitHub PR metadata | `GITHUB_METADATA_VERIFIED` | OPEN/DRAFT, not merged (조회 시점 기준) |
| PR #41 report conformance | GitHub PR metadata | `GITHUB_METADATA_VERIFIED` | merged, CI/pytest 수치는 PR_REPORTED |
| 24/7 실거래 자동화 | README는 명시적으로 미구현 | `README_REPORTED` | **목표 아키텍처**로만 표기 |
| SRC-012 논문 결과 | Stage 9 PDF 원문 대조 보고 | `PAPER_TEXT_VERIFIED_NOT_REPLICATED` | 저자 보고 수치, MoneyLab 수익성 근거 아님 |

#### 판정 로직

`CODE_AND_CONTRACT_INSPECTED`는 테스트 PASS를 뜻하지 않는다. `GITHUB_METADATA_VERIFIED`는 과학적 결과의 검증을 뜻하지 않는다. `README_REPORTED`는 README가 참이라고 확증한 상태가 아니다. 보고서에서 기술 제안은 `PROPOSED`, 검증되지 않은 성과는 `UNVERIFIED`로 유지한다.

#### 사용자 요구 반영: 기술보고서 본문과 추적성 분리

12개 보고서의 본문은 **기술의 배경·메커니즘·구현·대안·검증·실패 조건·MoneyLab 적합성**에 집중한다. 파일 열람 과정, 이미지·PDF·프롬프트 분석 일지는 본문에서 제거하거나 부록/Source Register로 이동할 후보로 표시한다. 역사적 출처의 사실을 삭제하지 않고 별도 Provenance로 보존한다.
