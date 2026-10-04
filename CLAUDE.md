# CLAUDE.md

AI 코딩 에이전트를 위한 MoneyLab 작업 지침.

## 프로젝트

예측시장/투자 전략 연구용 Python 프로젝트. 최종 목표는 수익성이 검증된 자동매매이고, 현재는 v0.1 읽기 전용 Scanner 단계다.
자세한 내용은 README.md를 참고한다.

## 환경

- Windows, Python 3.14 (`C:\MoneyLab\.venv`). 실행할 때는 항상 `.\.venv\Scripts\python.exe`를 쓴다.
- 패키지는 `pip install -e . --no-deps`로 설치되어 있다 (src layout).
- 테스트는 `.\.venv\Scripts\python.exe -m pytest`로 돌린다. 오프라인으로 실행되며 모두 통과해야 한다.
- 실행: `python -m moneylab scan [--source fixture]`, `python -m moneylab diagnose`
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

- `scanner/`, `strategy/`, `risk/`, `backtest/`, `paper/`, `analytics/`는 `providers.polymarket`를 import하지 않는다. `domain.Market`과 `MarketDataProvider`에만 의존한다.
- Provider는 실패할 때 `ProviderError`만 던진다. Scanner는 이를 `ScanResult.error`로 반환하고 프로그램을 종료시키지 않는다.
- 수익성 지표는 `analytics/metrics.py`의 순수 함수로 계산한다. 백테스트, 페이퍼, 라이브가 같은 함수를 쓴다.
- 비용(수수료, spread, slippage)을 뺀 순수익(net) 기준으로 평가한다. 총수익(gross) 엣지만으로 전략을 채택하지 않는다.
- 원본 데이터는 `data/raw/<provider>/`, 가공 데이터는 `data/processed/`에 둔다. 둘 다 git에서 제외한다.

## 작업 방식

- 기능을 구현하면 직접 실행하고 테스트한다. 실패하면 원인을 분석하고 고친 뒤 다시 테스트한다.
- 새 동작에는 오프라인 테스트를 추가한다 (`tests/conftest.py`의 `FakeSession`, `make_response` 활용).
- fixture의 출처(실제 캡처인지 합성인지)를 `tests/fixtures/README.md`에 기록한다.
