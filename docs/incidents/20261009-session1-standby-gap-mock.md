# 2026-10-09 session 1 수집 중 326 s 공백 (모의 조사)

> 모의(재현) 보고서다. agent workflow 2-4 Phase 2에서 `incident` Skill을 실세션으로 검증하려고 이미 끝난 수집 세션을 다시 조사했다.
> 새 장애가 아니며, 공백은 수집 당시 `QUALITY_NOTES.md`에 이미 기록되어 있다.

## 요약

`session_20261009T2206KST` KRW-BTC 6시간 수집은 `completed`로 정상 종료했다. 수집 중 326 s 데이터 공백이 1건 있었고,
같은 시각에 Windows Kernel-Power 대기 진입·복귀 이벤트(506/507, Idle Timeout)가 기록되어 있다.
연구 run `session_20261009T2206KST__20261010T062347Z`의 test split 해시는 manifest와 일치하고, 열렸다는 흔적은 없다.

## 분류

- `collection` (수집 중 공백 1건, 수집 자체는 정상 종료)
- `environment` (절전 대기와 시각이 겹침)

## 사실

시각: KST = UTC+9.

- 수집 상태 `completed`, `termination_reason` `completed`, `provenance` `real`.
  run 시작 2026-10-09T13:06:56Z (22:06:56 KST), 종료 2026-10-09T19:06:56Z (2026-10-10 04:06:56 KST), seq 1–198120.
  출처: `data/raw/upbit/research/session_20261009T2206KST/KRW-BTC/state.json`
- 같은 파일의 counters: connection 2, disconnect 2, orderbook 170779, trade 25222, status 2115, segments 9688.
  `last_error`는 `disconnected`, `status_code` null, `connection closed (code=None, reason='no close frame received or sent')`.
  HTTP 상태 코드는 기록되지 않았다.
- `record-verify`: `Integrity OK`, lines 198120, span 21,599 s, `warning: gap of 326.0s before line 39358`. 경고는 이것 1건뿐이다.
- `replay-check`: errors 2, out-of-order 0, duplicates 0, parse errors 0, late events 0, inter-message max 326035.0 ms.
  orderbook 메시지는 모두 30 units. dataset 723,986,013 bytes.
- `QUALITY_NOTES.md`(run 디렉터리) 11–19행: 326 s 공백 1건. 23:18:10.57–.69 KST에 늦게 도착한 메시지(recv − exchange 약 326 s)가 있었고,
  23:18:10.70 KST에 연결이 close frame 없이 닫힌 뒤 재연결했다. 공백 구간은 사전등록 규칙에 따라 `gap` 318행과 `warmup`으로 처리됐다.
- `wevtutil` (필터 2026-10-09T13:00:00Z – 19:15:00Z, EventID 506/507), 출력의 `Date`는 KST로 읽었다 (Skill 4단계 주석):
  - 506 대기 진입, 사유 Idle Timeout: 2026-10-09 23:12:17 KST (14:12:17Z)
  - 507 대기 복귀, 사유 Input Mouse: 2026-10-09 23:18:10 KST (14:18:10Z)
  - 506/507/506 (Idle Timeout, AC/DC Display Burst): 2026-10-10 02:18:39–02:18:46 KST (17:18:39–17:18:46Z)
  - 출력 시각이 모두 필터 범위를 KST로 옮긴 22:00–04:15 안에 있다. 이것도 `Date`가 로컬 시각이라는 주석과 맞는다.
- `clock_monitor.jsonl` 마지막 20건 (18:47Z–19:06Z): 모두 `measurement_status` ok, offset −117.5 ~ −115.4 ms, spread 1 ms 미만.
  manifest의 시계 요약: offset min −235.96 ms, max −115.40 ms, median −152.03 ms, 측정 332회, `clock_quality_status` `WARNING`.
- `w32tm /query /status` (조회 시점 2026-10-10): source `time.windows.com,0x9`, root dispersion 0.1793 s, poll 14 (16384 s).
  나머지 필드는 콘솔 코드 페이지 때문에 글자가 깨져서 미확인이다.
- `powercfg /a`: 출력이 깨져서 사용 가능한 대기 상태 목록은 미확인이다. 읽을 수 있는 토큰은 "S0 ... 네트워크"(S0 저전력 유휴로 보임),
  사용 불가 S1/S2/S3다.

## 가설

- H1 (유력): 23:12:17 KST에 유휴 시간 초과로 대기(S0 저전력 유휴)에 들어가 WebSocket 수신이 멈췄고, 23:18:10 KST에 마우스 입력으로
  복귀하자 버퍼에 쌓인 메시지가 한꺼번에 들어온 뒤 연결이 닫혔다. 근거: 506/507 시각이 공백 끝(23:18:10.57–.70) 및
  공백 길이(약 326 s, 대기 구간 353 s)와 겹친다. 대기 진입 후 수신이 바로 끊기지 않았을 수 있어 두 길이가 정확히 같지는 않다.
  확인하지 않은 부분: 대기 중 NIC 동작, 서버가 연결을 닫은 것인지 클라이언트가 닫은 것인지.
- H2 (낮음): 대기와 상관없는 네트워크 단절이 우연히 겹쳤다. 반박할 증거도 확인할 증거도 없다.
- 02:18 KST의 대기 506/507은 약 2–7 s로 짧았고 record-verify가 그 시각에 공백 경고를 내지 않았다. 영향이 없었던 것으로 보이지만
  공백 경고 기준값은 이번에 확인하지 않았다.

## 증거

```bash
git status --short  # [A]
./.venv/Scripts/python.exe -m pytest -q tests/test_repo_hygiene.py  # [A]
cat data/raw/upbit/research/session_20261009T2206KST/KRW-BTC/state.json  # [A]
./.venv/Scripts/python.exe -m moneylab record-verify data/raw/upbit/research/session_20261009T2206KST/KRW-BTC  # [A]
./.venv/Scripts/python.exe -m moneylab replay-check data/raw/upbit/research/session_20261009T2206KST/KRW-BTC  # [A]
sha256sum data/processed/research/*/locked/test.jsonl.gz  # [A]
```

- `wevtutil qe System` (EventID 506/507, UTC 필터): 위 사실 절의 5건.
- guard 차단: 없음. 조사 중 승인 창: 에이전트 쪽에서는 관측되지 않음.
- Skill 절차 결함 (이번 조사에서 발견): Skill 4단계의 `w32tm /query /status`와 `powercfg /a`를 Git Bash에서 그대로 실행하면
  MSYS 경로 변환 때문에 실패한다 (`C:/Program Files/Git/query ...`, `powercfg` 인자 오류). `MSYS_NO_PATHCONV=1` 접두어를 붙여
  1회 재시도했고 둘 다 exit 0으로 끝났다. 두 명령의 출력은 CP949라서 글자가 깨진다.

## 영향

- 데이터: 326 s 구간의 시장 데이터가 없다. 사전등록 규칙대로 gap/warmup으로 처리됐고 해당 창의 feature·label은 NaN이다.
- 연구: test split이 잠겨 있어 이번 조사로 바뀐 것이 없다. 공백이 결과(112 REJECT)에 준 영향은 이번에 평가하지 않았다.

## 무결성

- `tests/test_repo_hygiene.py`: 59 passed.
- `git diff --stat HEAD -- configs docs src`: 변경 없음 (추적 파일 기준).
- run manifest: `dataset_sha256` `af3aaf29e345c4e103ceece417a205be3bc74cbb6ae60f3034f530bdcef512fc`,
  `raw_manifest_sha256` `1ffffde075855bfb162bc5f7e10eb384f871f9048ca76848f2d5bd23ff1ec1c1`,
  `preregistration_sha256` `f86792c0ffa95b9f39b9f707c07b991f4a2795c87d8a7409e4aadcf84f181e74`,
  `config_sha256` `c16b22a3fe820e0f234e0c04e9ceff135cfeabb941519c6b44d47eb18229cd5f`.
- test split: manifest `test_sha256` `fee8ca28546e625f348a98553b351e04f1f5a491a209255534e2f3b03735343d`와 단독 `sha256sum` 결과가 일치한다.
  manifest에는 open·final 관련 필드가 없고, run 디렉터리에는 `QUALITY_NOTES.md`, `grid_trainval.jsonl.gz`, `locked`, `manifest.json`, `stats`만 있다.
  test가 열렸다는 흔적은 없다.

## 복구 제안

- collection: raw 데이터를 보존한다. 이 세션은 정상 종료했으므로 이어서 수집할 필요는 없다. 공백이 있는 이 데이터의 품질 판정은 사용자가 한다.
- environment: 장시간 수집 전에 유휴 대기 시간 설정을 사용자가 직접 확인한다 (에이전트는 전원 설정을 바꾸지 않는다).
  `powercfg /a` 출력이 깨져서 대기 상태 목록은 사용자가 직접 확인해야 한다.
- Skill 개선 (사용자 결정, `.claude/` 수정은 `[B]`): `incident` 4단계의 `w32tm`, `powercfg` 줄에 `MSYS_NO_PATHCONV=1`을 붙이고,
  출력이 CP949로 깨진다는 주석을 단다.
