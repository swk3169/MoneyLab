# CLAUDE.md

AI 코딩 에이전트를 위한 MoneyLab 작업 지침.

## 프로젝트

예측시장/투자 전략 연구용 Python 프로젝트. 최종 목표는 수익성이 검증된 자동매매이고, 현재는 v0.3 단계(읽기 전용 Scanner + fixture 기반 오프라인 전략 시뮬레이션 + 실데이터 Recorder/Replay)다. 실거래 adapter는 설계 문서(`docs/live_execution_design.md`)만 있다.
자세한 내용은 README.md를 참고한다.

## 환경

- Windows, Python 3.14 (`C:\MoneyLab\.venv`). 실행할 때는 항상 `.\.venv\Scripts\python.exe`를 쓴다.
- 패키지는 `pip install -e . --no-deps`로 설치되어 있다 (src layout).
- 테스트는 `.\.venv\Scripts\python.exe -m pytest`로 돌린다. 오프라인으로 실행되며 모두 통과해야 한다.
- 실행: `python -m moneylab scan [--source fixture]`, `diagnose`, `book`, `simulate --strategy mm|mispricing [--recording <dir>]`, `record [--source fixture]`, `record --provider upbit [--source fixture] [--duration N]`, `record-verify <dir>`, `replay-check <upbit dir>`, `clock-monitor`, `research-build <upbit dir> [--dry-run]`, `research-stats <run>`, `research-final <run>`, `candles-pull --interval day|hour (--last N | --start --end) [--dry-run] [--source fixture]`, `candles-verify <pull dir>`
- 의존성을 추가하면 `pyproject.toml`(범위)과 `requirements*.txt`(고정 버전)를 함께 갱신하고, Python 3.14 호환성을 확인한다.

## 절대 규칙

1. 사용자가 명시적으로 승인하기 전에는 **실제 주문, 지갑 연결, 개인키·seed phrase 사용, 자동매매, 실거래 자금 사용을 구현하지 않는다.**
2. 비밀정보는 코드, 로그, fixture, 커밋에 넣지 않는다. 비밀값은 환경변수로만 받고, 출력은 `core/redaction.py`를 거친다.
3. `.env`는 커밋하지 않는다. `.env.example`만 커밋한다.
4. VPN, 프록시, 지역 제한 우회 기능은 구현하지 않는다. HTTP 451, 403의 원인을 단정하지 않는다. 사실과 가설을 구분해서 보고한다.
5. API 응답 구조를 추측하지 않는다. 실제 응답(`data/raw/`)을 확인한 뒤 파서를 바꾼다. 확인하지 못한 필드는 주석에 미검증이라고 표시한다.
6. 모든 네트워크 호출은 `core/http.HttpClient`를 통해 한다 (timeout, 재시도, 진단 포함).
7. 사용자가 요청하기 전에는 git commit이나 push를 하지 않는다.

## 아키텍처 규칙

- `scanner/`, `strategy/`, `risk/`, `backtest/`, `paper/`, `analytics/`, `pnl/`, `sizing/`은 `providers.polymarket`를 import하지 않는다 (`tests/test_architecture_and_cli.py`가 검사). `domain`과 `providers.base`(`MarketDataProvider`, `OrderBookProvider`)에만 의존한다.
- Recorder는 HTTP 451/401/403을 재시도하지 않고 즉시 중단한다. 기록 파일은 `storage/atomic.py`로만 쓴다.
- Provider는 실패할 때 `ProviderError`만 던진다. Scanner는 이를 `ScanResult.error`로 반환하고 프로그램을 종료시키지 않는다.
- 수익성 지표는 `analytics/metrics.py`의 순수 함수로 계산한다. 백테스트, 페이퍼, 라이브가 같은 함수를 쓴다.
- 비용(수수료, spread, slippage)을 뺀 순수익(net) 기준으로 평가한다. 총수익(gross) 엣지만으로 전략을 채택하지 않는다.
- maker rebate와 liquidity reward는 `estimated_*`와 `realized_*`로 분리한다. 추정치는 실현 PnL과 채택 판단에 넣지 않는다.
- 원본 데이터는 `data/raw/<provider>/`, 가공 데이터는 `data/processed/`에 둔다. 둘 다 git에서 제외한다.
- `research/`는 provider를 import하지 않는다. 사전등록(`docs/research_v04_preregistration.md`, `configs/research_v04.toml`)을 바꾸면 새 study다. test split은 `research-final`로만, run당 한 번 연다.

## v0.6 캔들 수집 (`candles-pull`, `candles-verify`)

- 모드는 세 가지다. `--dry-run`은 요청 계획(엔드포인트, 범위 UTC·KST, page_count, 최대 요청 수, 저장 위치)만 출력하고 요청·파일 쓰기가 없다. `--source fixture`는 합성 `tests/fixtures/upbit_candles_synthetic.json`으로 네트워크 없이 돌고 `data/raw/upbit/candles_v06-fixture/`에 `provenance = fixture`로 쓴다. 기본(live)은 Upbit 공개 REST(`/v1/candles/days`, `/v1/candles/minutes/60`)를 호출하고 `data/raw/upbit/candles_v06/`에 `provenance = real`로 쓴다.
- **live 실행은 매번 사용자의 명시적 승인을 받는다.** guard와 `settings.json`에는 아직 `candles-pull` 승인 규칙이 없어서 확인 창이 뜨지 않는다. 승인 전에 먼저 같은 인자로 `--dry-run`을 실행해 보여준다. 승인 범위(구간 수, 요청 수)를 넘지 않도록 `--max-pages`를 지정한다.
- `--last N`은 진행 중인 구간을 포함한 최근 N개 구간이다. 진행 중 캔들은 확정 규칙(구간 끝 + 120 s ≤ 로컬 수신 시각과 서버 `Date` 중 이른 쪽)에 따라 제외된다. UTC 00:00~00:05(KST 09:00~09:05)와 매 정시 직후 3분에는 실행하지 않는다.
- 수집마다 새 디렉터리(`<interval>_<market>_<UTC stamp>/`)를 만들고 기존 파일은 덮어쓰지 않는다. `pages/NNNN.json`은 gzip을 푼 응답 본문이고 SHA-256은 이 바이트에 대해 계산한다.
- live 수집 뒤에는 `candles-verify <pull dir>`로 해시·파일 목록·Replay 일치를 확인한다. 이 명령은 오프라인이고 파일을 쓰지 않는다. 수집 원본은 고치거나 지우지 않는다.
- 캔들 수집은 데이터 검증이다. 사전등록(`docs/research_v06_preregistration_draft.md`)을 고정하기 전에는 가격·수익률을 분석하지 않는다.

## 작업 방식

- 기능을 구현하면 직접 실행하고 테스트한다. 실패하면 원인을 분석하고 고친 뒤 다시 테스트한다.
- 새 동작에는 오프라인 테스트를 추가한다 (`tests/conftest.py`의 `FakeSession`, `make_response` 활용).
- fixture의 출처(실제 캡처인지 합성인지)를 `tests/fixtures/README.md`에 기록한다.
