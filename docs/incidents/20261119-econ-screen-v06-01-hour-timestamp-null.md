# 2026-11-19 ECON-SCREEN-V06-01 1시간봉 수집 중단: timestamp null

> 기존 조사 결과로 작성한 기록이다. 이 기록을 쓰면서 원본 pull을 다시 열거나 verify·재수집·복구를 하지 않았다.

## 요약

ECON-SCREEN-V06-01 RUN의 COLLECT_LIVE에서 일봉 pull은 정상 완료됐고, 1시간봉 pull은 응답 해석 실패
(`CandleParseError: timestamp: expected integer ms, got None`)로 중단됐다. 실패 페이지의 4행에서 `timestamp` 키는 있었고
값이 null이었다. 수집기는 그때 정수만 받았다. 01은 수집 단계에서 중단 종결됐고(경제성 결과 없음), 같은 질문은 별도로
사전등록한 후속 study ECON-SCREEN-V06-02에서 다룬다.

## 분류

- `collection` (1시간봉 수집 중 해석 실패로 중단, 일봉은 정상 완료)
- `parser` (실제 응답 값이 수집기의 형식 가정과 다름)

## 사실

시각: KST = UTC+9.

- 일봉 pull `day_KRW-BTC_20261119T190841411418Z`: 2026-11-19 19:08Z live 수집, status `complete`, 페이지 13개(상한 15),
  받은 행 2,380, 보존 캔들 2,380, 첫·마지막 캔들 2017-09-25·2024-03-31(UTC), 중복·누락 bucket·값 이상 0,
  빈 페이지 종료 경고 1건("treated as earliest available (unverified)"). 수집 중 verify와 별도 `candles-verify` 1회가 모두 ok.
- 1시간봉 pull `hour_KRW-BTC_20261119T190858838984Z`: 19:08:53Z 시작, exit 1, pull.json `status` `failed`,
  `error` `CandleParseError: timestamp: expected integer ms, got None`, 품질 보고 없음.
- 저장된 페이지와 meta는 각 222개(0000–0221)다. meta 222개의 `attempts`는 모두 1이므로 HTTP 요청은 222회, 재시도는 0회였다
  (승인 상한: 페이지 319, HTTP 957). HTTP 451·401·403과 페이지 상한 오류는 없었다.
- 실패 페이지는 마지막으로 저장된 `pages/0221.json`이다(수집기는 원본을 해석 전에 저장한다). meta: HTTP 200, 요청
  `to` = 2019-03-14T15:00:00Z.
- 0221은 JSON 배열 200행이다. 모든 행의 필드 이름은 같은 11개(`market`, `candle_date_time_utc`, `candle_date_time_kst`,
  가격 4개, 누적 2개, `timestamp`, `unit`)다. `timestamp`는 int 196행, null 4행(인덱스 179, 180, 181, 182)이다.
  그 4행에서 null인 필드는 `timestamp` 하나이고 두 시각 필드는 문자열로 있다.
- 직전 페이지 `pages/0220.json`(요청 `to` 2019-03-23T02:00:00Z)은 200행, 같은 11개 필드, `timestamp` 200행 모두 int다.
- 그때 수집기(`parse_candle`)는 `timestamp`가 bool이 아닌 int가 아니면 `CandleParseError`로 수집 전체를 중단했다.
  `timestamp`는 구간 마지막 체결 시각(ms)이며, 캔들 기준 시각(`candle_date_time_utc`, 구간 시작)과 다른 필드다.
- Upbit 공식 문서(`https://docs.upbit.com/kr/reference/list-candles-days`, `.../list-candles-minutes`, 2026-11-20 확인)는
  `timestamp`를 "해당 캔들의 마지막 틱이 저장된 시각의 타임스탬프 (ms)", `integer`/`int64`, required로 정의하고
  nullable·null 의미·과거 캔들 설명은 명시하지 않는다.
- 조사 범위: 가격·거래량·체결대금·수익률 값은 사람이 열람하거나 출력하지 않았다. 일봉 수집 출력의 날짜·개수와
  1시간봉 두 페이지의 구조 정보(필드 이름, 형식, null 여부, 행 인덱스)만 보았다. null 4행의 시각 값은 출력하지 않았다.
- 01 RUN에서 PULL_REVIEW, PREPARE, RUN, INTEGRITY_CHECK, RESULT_VIEW는 수행하지 않았고 성과를 계산하지 않았다.
  01 RUN은 2026-11-19 19:27Z 중단 종결 보고로 닫혔다.

## 가설

- null의 원인은 확인되지 않았다. 후보는 과거 구간 데이터의 마지막 틱 시각 결측이나 이관 과정의 누락 등이며, 모두
  API 수준에서 검증되지 않았다.
- null 행의 가격·거래량 값이 다른 행과 같은 의미로 유효한지는 확인되지 않았다(공식 문서에 근거 없음).
- 같은 구간을 다시 수집해도 null이 다시 나올 가능성이 있으나 확인되지 않았다.

## 증거

```bash
git -C C:/MoneyLab-futval-v8-01-precheck log -1 --format="%H %T"  # [A]
./.venv/Scripts/python.exe -m moneylab candles-verify data/raw/upbit/candles_v06/day_KRW-BTC_20261119T190841411418Z  # [A] (01 수집 직후 1회, 이 기록 작성 때는 재실행하지 않음)
```

- 1시간봉 실패 출력: 수집 명령의 stdout(오류 문구와 evidence 경로).
- 구조 조사: pull.json의 status·error·pages 목록, meta 222개의 `attempts`, 0220·0221의 필드 이름·형식·null 여부만 읽는
  읽기 전용 스크립트 출력(값은 출력하지 않음).
- 공식 문서 확인: 위 두 문서 페이지의 렌더링 본문과 그 안의 OpenAPI 정의(별도 조회 에이전트, 캔들 API 호출 없음).
- guard 차단: 없음.

## 영향

- 데이터: 일봉 pull은 complete이고 보존된다. 1시간봉 pull은 2019-03-14 이전 구간을 받지 못한 부분 pull이며, 평가 입력으로
  쓰지 않는다.
- 연구: ECON-SCREEN-V06-01은 수집 단계에서 중단 종결됐고 경제성 결과가 없다. 01 사전등록(SHA-256
  2ff766fa8e60adbc107b1ffe9ae4df30c455b616cd5345154704ff928b74705d)과 중단 기록은 바뀌지 않는다.
- 후속: 별도 study ECON-SCREEN-V06-02를 사전등록했다(SHA-256 c6bd5e7eb0bcd8d44e668a9289ea67dafc97462063003cc1f9d183c18f092f81).
  02는 `timestamp` null을 보고 전용으로 분류하고, 일봉 재사용 조건과 1시간봉 1회 새 수집을 정한다.

## 무결성

- 보존 대상(이름·파일 수·파일 해시 목록 다이제스트만 확인, 내용은 열지 않음)
  - `data/raw/upbit/candles_v06/day_KRW-BTC_20261119T190841411418Z/`: 27개, 93771f84d66b375e7e779124c46b4e62a7932d976fbfcc67b67551db5893dae8
  - `data/raw/upbit/candles_v06/hour_KRW-BTC_20261119T190858838984Z/`: 445개, da643a341087b6e9de0bfe959988117714a492a97b1dde3ff2d6d7d8f5187e51
- 두 pull은 수정·삭제·이름 변경되지 않았고 자동 재시도도 없었다.
- 01 RUN Work Order(C1 bee1d2e3b3f0863c3a82a6bc2221914cf8a066ab)는 바뀌지 않았다.

## 복구 제안

- 이 기록 시점에 재수집·재사용 검증·복구는 수행하지 않았다.
- 후속 진행은 ECON-SCREEN-V06-02 사전등록 13절 순서를 따른다: 제한 구현(`timestamp` null 보존·보고, 02 식별 연결),
  일봉 재사용의 오프라인 검증, 1시간봉 dry-run과 별도 승인 live 1회, 품질 확인 등. 각 단계는 별도 계약과 승인이 필요하다.
- 실패한 1시간봉 pull은 증거로 보존하고 어떤 단계의 입력으로도 쓰지 않는다.
