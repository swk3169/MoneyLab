# FUTVAL-V8-01 사전등록 후보: V0 futility 검정의 iid 유한 표본 기각률

상태: 고정(FROZEN). 사용자가 승인한 바이트로 이 문서의 최초 고정 커밋이 완료되는 시점에 효력이 생긴다. 그 전에는 미발행 후보이며 연구 실행 권한을 만들지 않는다.
사전등록 판: v1. 판정 규칙 판: FUTVAL-V8-01-decision/1.

## §0 선정 경위와 지위

- 이 질문은 기존 사후 진단(BT4-FUTILITY-01 DIAG, BT4-FUTILITY-02)의 결과를 본 뒤 선정했다. 이 study는 그 결과의 재현이 아니며, 새 표본으로 사전 고정한 질문에 답한다.
- 기존 결과 수치와 판정 라벨은 이 문서에 쓰지 않고, 판정이나 사전확률에도 쓰지 않는다.
- 기존 사전등록, 결과 제한(D4 결과 공개 미승인, V-1 분포 미승인), PR #40의 DO_NOT_MERGE, 기존 미완료 의무는 바꾸지 않는다.
- 증거 등급: SYNTHETIC / NOT_EVIDENCE. 수익성, 경제적 가치, 실거래 적합성에 대한 결론은 내리지 않는다.

## §1 질문

고정된 V0 futility 검정 구현(B = 9,999, mean_block = 20, α = 0.05)이 iid Normal 경계(truth 연 SR = θ)에서 다음을 만족하는지 12개 (n, θ) 셀에서 판정한다.
- 축 A: 기각률이 명목 α를 넘는가.
- 축 B: 기각률이 α + ε 미만인가.

## §2 검정 대상 절차 (V0)

- 대상: procedures.mean, procedures.sd, procedures.futility_delta, procedures.bootstrap_means, procedures.futility_pvalue, procedures._mc_p, stats._blocks, stats._Prefix(8개). 변경 없이 호출하거나 그 호출 안에서 쓰인다.
- 계산:
  - m = mean(r)
  - δ̂ = futility_delta(θ, r) = θ·s/√365, s는 n−1 분모 표본 표준편차
  - boot = bootstrap_means([r], mean_block=20, resamples=9999, seed=boot_seed)[0]
  - p = futility_pvalue(m, boot, δ̂) = (1 + count)/10000, count = #{b : boot_b − m + δ̂ ≤ m}
- 기각 지시변수(정상 복제만): I = 1{p ≤ 0.05}. 이는 count ≤ 499와 같다.
- 절차의 가설: H0 μ ≥ δ 대 H1 μ < δ, 왼쪽 단측.
- 이 정의는 v0.6 초안 10.6 (1)과 montecarlo.Procedure 기본값(mean_block 20, bootstrap 9,999)과 같다.
- src/moneylab/research/v06/procedures.py와 src/moneylab/research/stats.py는 고정 커밋 시점의 Git blob과 같아야 한다. 다르면 STOP한다. 새 코드는 두 파일을 수정하지 않는다.

## §3 DGP와 셀

- P0: r_t = μ + σ·z_t, z_t는 iid N(0, 1), σ = 0.70/√365, μ = θ·σ/√365. truth 연 SR = θ이고 항상 노출한다.
- V0가 척도 불변이라는 성질은 코드 식에서 도출한 것이며 §9 T1에서 확인한다.
- 셀 12개, 고정 순서는 n 오름차순 다음 θ 오름차순(c = 1..12).
  - n ∈ {365, 731, 1096, 2227}
  - θ ∈ {0.3, 0.5, 0.7}
- 셀당 R = 10,000, rep = 0..9999.
- 복제마다 길이 n의 독립 계열을 새로 생성한다. 창을 공유하거나 중첩하지 않는다.
- 제외: E1과 의존성·피드백 DGP, GARCH-t, 노출 셀, 914일 창, α = 0.10, 검정력 셀, 귀무 내부 셀, 보정 절차, 대체 검정 비교.

## §4 Seed와 난수 경로

- BASE = 20261118(고정값). BASE는 0 이상 2^63 − 1 이하의 정수다.
- 직렬화(Python 3):
  - s = ns + "|v1|BASE=" + str(BASE) + "|n=" + str(n) + "|theta=" + th + "|rep=" + str(rep) + "|stream=" + st
  - seed = int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")
  - ns ∈ {"FUTVAL-V8-01", "FUTVAL-V8-01-PERF", "FUTVAL-V8-01-TEST"}, th ∈ {"0.3", "0.5", "0.7"}, st ∈ {"data", "boot"}
  - str(int)는 부호 없는 10진수이며 앞자리 0이 없다. 모든 문자는 ASCII이고 공백은 없다.
- 이름공간: 본 실행 "FUTVAL-V8-01", 성능 측정 "FUTVAL-V8-01-PERF", 테스트·smoke "FUTVAL-V8-01-TEST".
- data: rng = random.Random(data_seed). t = 0..n−1 순서로 z_t = rng.gauss(0.0, 1.0)을 뽑고 r_t = μ + σ·z_t(float)로 만든다.
- boot: bootstrap_means(..., seed=boot_seed). 내부에서 random.Random(boot_seed)와 stats._blocks(randrange, random)를 쓴다.
- 고유성 사전 검사:
  - 본 실행 이름공간의 seed 240,000개(12셀 × 10,000 rep × 2 stream)의 서로 다른 값의 수가 240,000인지 확인한다.
  - seed 값만 계산하며 데이터 생성, p 계산, 결과 열람을 하지 않는다. 통계 계산 전의 결정적 검사이며 후속 실행 승인에 포함할 수 있다.
  - 중복이 있으면 STOP한다. 해결은 직렬화를 바꾼 새 study로만 한다.
- 한계: seed가 서로 다르다는 것은 MT19937 난수열의 통계적 독립을 수학적으로 보장하지 않는다. 독립은 실용적 가정이다. 기존 이름공간 seed와의 값 단위 교차 대조는 하지 않는다.

## §5 퇴화·실패·분모

- 정상 복제: 모든 호출이 예외 없이 반환하고 s > 0이며 m·δ̂·p가 모두 유한값인 복제. 셀 c에서 정상 복제 중 I = 1인 수를 K_c라 한다.
- 퇴화 복제: 모든 호출이 예외 없이 반환했지만 s = 0이거나 m·δ̂·p 중 비유한값이 있는 복제. 그 수를 D_c라 한다. 퇴화는 반환값 검사로 판정하며 예외가 아니다.
- 실패: 데이터 생성, 함수 호출, 쓰기 중 예외. 본 실행 전체를 STOP한다. 대체 복제, 재추출, seed 교체, 재시도, 부분 결과 사용은 없다. 쓰기가 끝난 출력은 보존한다.
- 분모는 모든 셀에서 R = 10,000으로 고정하며 퇴화 복제를 포함한다.
- 축 A 기각 수 X_A,c = K_c(퇴화를 비기각으로 셈). 축 B 기각 수 X_B,c = K_c + D_c(퇴화를 기각으로 셈).
- D_c = 0이면 두 축은 같은 이항 표본을 쓴다.
- D_c > 0이면 [K_c/R, (K_c + D_c)/R]는 이 표본에서 퇴화 처리 방식에 따라 가능한 기각 비율의 범위다. 모집단 기각률이 이 범위 안에 있다는 뜻이 아니다. 각 축은 자기 주장에 보수적인 쪽 수로 판정한다.
- D_c는 셀별로 보고하며, 그 크기 때문에 판정이나 설계를 바꾸지 않는다.

## §6 판정

- 상수(유리수): α = 1/20, ε = 1/100, α + ε = 3/50, λ = 1/40, t_j = λ/(13 − j) (j = 1..12).
- 축 A (기각률 초과)
  - H0_A,c: π_c ≤ α 대 H1_A,c: π_c > α.
  - p_A,c = P(Bin(R, α) ≥ K_c).
  - Holm, FWER λ: p_A 오름차순(같은 R과 α이므로 K 내림차순)으로 정렬하고 동률은 셀 고정 순서를 따른다. j = 1..12에서 p_(j) ≤ t_j이면 기각하고 진행한다. 처음 비기각에서 멈추고 이후 셀은 모두 비기각이다.
  - 셀 판정: SIZE_EXCESS_CONFIRMED / SIZE_EXCESS_NOT_CONFIRMED. 집계: ANY_SIZE_EXCESS_CONFIRMED (YES/NO).
- 축 B (허용 한도 이내)
  - H0_B,c: π_c ≥ 3/50 대 H1_B,c: π_c < 3/50.
  - p_B,c = P(Bin(R, 3/50) ≤ K_c + D_c).
  - 셀 판정: p_B,c ≤ λ이면 WITHIN_TOLERANCE_SHOWN, 아니면 WITHIN_TOLERANCE_NOT_SHOWN.
  - 집계: 12셀이 모두 WITHIN_TOLERANCE_SHOWN일 때만 ALL_CELLS_WITHIN_TOLERANCE_SHOWN = YES. 귀무는 "어느 한 셀이라도 π_c ≥ 3/50"이며, 셀별 수준 λ 검정이 모두 기각될 때만 주장하므로(IUT) 집계 주장의 수준은 λ다. 셀별 판정에는 가족 단위 오류 통제가 없다.
- 오류 주장의 범위: 축 A 가족 FWER ≤ λ와 축 B 집계 주장 수준 ≤ λ는 각각 따로 성립한다. 두 축을 합친 하나의 오류율은 보장하지 않는다. 두 보장 모두 복제 간 독립과 이항 모형을 전제로 한다.
- 두 축은 동시에 참일 수 있다(α < π_c < 3/50). SIZE_EXCESS_NOT_CONFIRMED는 "초과 없음"이 아니다. WITHIN_TOLERANCE_NOT_SHOWN은 "허용 폭 초과"가 아니다.
- 보고 구간(판정에 쓰지 않음): X ∈ {K_c, K_c + D_c}마다 양측 95% Clopper–Pearson 구간.
  - 하한 L = inf{π : P(Bin(R, π) ≥ X) > 0.025}, X = 0이면 0.
  - 상한 U = sup{π : P(Bin(R, π) ≤ X) > 0.025}, X = R이면 1.
- 설계 참고값: R = 10,000에서의 셀당 검정력(정규 근사)은 설계 참고용이며 보장이 아니다. 판정과 해석에 쓰지 않는다.

## §7 수치 구현

- 최종 판정 기준은 정확한 정수 임계값이다. 꼬리확률이 X에 대해 단조이므로 다음과 같다.
  - 축 A: p_A(K) ≤ t_j ⇔ K ≥ a_j. a_j는 P(Bin(R, 1/20) ≥ a) ≤ t_j를 만족하는 최소 정수 a.
  - 축 B: p_B(X) ≤ λ ⇔ X ≤ b. b는 P(Bin(R, 3/50) ≤ x) ≤ λ를 만족하는 최대 정수 x.
  - Holm은 K 내림차순(동률은 셀 순서) 정렬 뒤 K_(j) ≥ a_j 비교와 같다.
- 방법 1(기준, 정확): a_1..a_12와 b를 공통분모(20^R, 50^R)를 쓴 정확 정수 산술로 계산한다. 같은 정수를 내는 다른 정확 산술로 구현해도 된다. R, α, ε, λ만으로 결과 열람 전에 계산한다.
- 방법 2(검증, 근사): 로그 공간 누적(math.lgamma 기반)으로 각 임계값과 그 이웃(축 A는 a_j − 1, 축 B는 b + 1)의 꼬리확률을 계산한다. 방법 1의 꼬리확률과 상대 오차 10^-9 이내이고 판정 방향이 같아야 한다.
- 방법 2 검증이 실패하거나, 어느 방법에서든 예외나 비유한값이 나오면 COMPUTATION_FAILURE로 STOP한다. 연구 결과가 아니라 계산 실패로 기록하며 판정을 내리지 않는다. 계산 방법 변경은 새 판정 규칙 판이 필요하다.
- 보고용 p_A·p_B는 방법 2로 계산해 보고만 한다. 판정은 정수 비교 결과다.
- CP 보고 구간: 방법 2 꼬리확률로 π ∈ [0, 1]에서 bisection한다. 중단 기준은 구간 폭 ≤ 10^-10 또는 200회 반복이다. 소수 6자리로 보고하고, 200회 안에 폭 기준을 못 채우면 CP_NOT_CONVERGED로 표시한다. 판정에는 영향이 없다.

## §8 적용 범위와 해석 제한

- 적용 범위: 지정한 12개 iid Normal 셀, 고정 구현(B 9,999, mean_block 20, α 0.05, 고정 커밋의 두 소스 파일), Python 3.14.8, 실행한 플랫폼.
- 의존성 DGP, 노출 전략, 다른 θ·n·B, 914일 창, 실데이터로 일반화하지 않는다.
- 판정명은 §6의 두 축 이름만 쓰며 포괄적 적합성 표현은 쓰지 않는다.
- 축 B 통과가 MC-V06 초과기각의 원인을 확정하거나 다른 원인을 배제하지 않는다. 축 A 확인이 원인을 귀속하지 않는다.
- 검정력과 절차의 전반적 유용성에 대한 결론은 내리지 않는다.

## §9 출력, 무결성, 재현성

- 본 실행 출력 디렉터리(로컬 ignored)
  - manifest.json: 식별(연구 ID, 사전등록 판, 판정 규칙 판), 코드(실행 커밋 SHA, procedures.py·stats.py·새 모듈·새 테스트 파일의 Git blob ID와 LF 기준 sha256, §2 대상 8개 각각의 inspect.getsource UTF-8 sha256), 환경(sys.version, platform.python_implementation(), sys.platform, 의존성은 표준 라이브러리와 moneylab뿐), 난수 규칙(§4 직렬화 형식, 이름공간, BASE, MT19937 경로). 다른 출력 파일의 해시는 담지 않는다.
  - design.json: 셀 목록과 순서, R, rep 범위, B, mean_block, α, ε, λ, t_j, 임계값 a_j·b, §7 방법 1·2의 경계 검증 기록, seed 고유성 검사 결과(개수와 통과 여부).
  - cells.json: 셀별 K, D, 보고용 p_A·p_B, 두 축 판정, CP 구간과 수렴 표시.
  - summary.json: ANY_SIZE_EXCESS_CONFIRMED, ALL_CELLS_WITHIN_TOLERANCE_SHOWN.
  - SHA256SUMS: 고정 목록 manifest.json, design.json, cells.json, summary.json 4개의 sha256만 담는다. 자기 자신과 execution.json은 담지 않는다.
  - execution.json: 시작·종료 시각, 경과 시간, worker 수, 호스트, 절대 경로, OS 세부, 병렬 효율. 실행 메타데이터이며 SHA256SUMS 대상이 아니다. 무결성 검사 범위 밖이고 결과 판정에 쓰지 않는다.
- 어떤 파일도 자기 자신의 해시를 담지 않는다. manifest.json은 SHA256SUMS의 해시를 담지 않는다. 순환 참조는 없다.
- 결과 4개 파일에는 시간, 경로, 호스트, worker 수를 넣지 않는다. 같은 플랫폼과 같은 Python에서 worker 수 1과 2의 결과 4개 파일과 SHA256SUMS는 바이트가 같아야 한다. 운영체제 간 바이트 동일성은 주장하지 않는다.
- 호스트, 절대 경로 등 로컬 메타데이터는 어떤 보고에도 복사하지 않는다.
- 출력은 storage/atomic으로만 쓴다. 데이터 파일을 먼저 쓰고 SHA256SUMS를 마지막에 쓴다. SHA256SUMS가 없는 디렉터리는 미완료다.
- 오프라인 테스트(이름공간 FUTVAL-V8-01-TEST 또는 고정 입력, 본 실행과 성능 측정 결과를 쓰지 않음)
  - T1 DGP의 μ·σ와 truth SR 해석식, 척도 불변 성질
  - T2 V0 호출이 procedures 직접 호출과 bit 단위로 같음. 운영 상수 B = 9999, mean_block = 20, α = 1/20
  - T3 직렬화 문자열과 seed의 고정 사례값, 고유성 검사, 중복 주입 시 STOP
  - T4 방법 1·2 꼬리확률이 소규모 R에서 일치, 경계 등호 사례
  - T5 임계값 변환(축 A·B)이 꼬리확률 직접 판정과 같음
  - T6 Holm 정렬·동률·중단 규칙
  - T7 판정 진리표(두 축 동시 참, 동시 거짓, D > 0)
  - T8 퇴화와 예외 구분, 예외 시 STOP, 재시도 없음
  - T9 COMPUTATION_FAILURE 경로
  - T10 CP bisection 중단 기준과 CP_NOT_CONVERGED
  - T11 worker 1과 2의 결과 파일 바이트 동일, execution.json 분리, SHA256SUMS 목록 고정
  - T12 두 소스 파일 blob 불변, storage/atomic 사용
  - 전체 pytest 통과
- 테스트는 로직 검사에 작은 B와 작은 R을 쓸 수 있다. 운영 상수는 T2로 확인한다. §6·§7 판정 코드를 smoke나 성능 측정 표본에 적용하지 않는다.

## §10 smoke, 성능 측정, 비용, 공개

- smoke
  - 이름공간 FUTVAL-V8-01-TEST, 운영 B = 9,999, 12셀 각 rep 0..1.
  - 별도 스키마 moneylab.futval_v8_01.smoke/1의 smoke.json과 SHA256SUMS를 쓴다. smoke.json은 자기 자신의 해시를 담지 않는다. SHA256SUMS는 smoke.json 하나의 sha256만 담고 자기 자신은 담지 않는다.
  - smoke.json 기록 항목: 식별, 셀별 완료 복제 수, 구조 검사(호출 반환과 값의 형식) 통과 여부.
  - p, 기각 지시변수, 기각률, K, D, 두 축 판정, 이를 복원할 수 있는 집계는 기록하거나 출력하지 않는다.
- 성능 측정
  - 이름공간 FUTVAL-V8-01-PERF, 운영 B = 9,999, θ = 0.5, n ∈ {365, 731, 1096, 2227} 각 rep 0..19(80 복제).
  - 측정 M1은 worker 1, M2는 worker W로, 같은 80개 seed를 쓰므로 데이터 생성과 통계 계산 작업량이 같다.
  - 별도 스키마 moneylab.futval_v8_01.perf/1의 perf.json에는 측정별 wall 시간, CPU 시간 합, n별 복제당 wall 시간, 최대 메모리, W, 병렬 효율 η = T_M1/(W·T_M2)만 기록한다.
  - p, 기각 지시변수, 기각률, K, D, 판정은 계산 후 버리며 기록하거나 출력하지 않는다.
  - W 허용 범위는 2 이상 os.cpu_count() − 1 이하의 정수다. W는 하드웨어 확인 뒤 성능 측정 실행 승인에 명시한다. 실행 승인에 W가 없거나, os.cpu_count()가 None이거나 확인되지 않거나, 허용 범위가 비어 있거나(os.cpu_count() < 3), 명시된 W가 범위 밖이면 성능 측정 전에 STOP한다.
  - 본 실행 worker 수는 자원 예산 승인에서 정한다. 결과 파일은 worker 수와 무관하다(T11).
  - 성능 측정의 규모·반복·W를 바꾸면서 연구 결과를 확인하는 것은 금지한다. 성능 측정 출력에는 연구 결과가 없다.
- 실행 비용: 실행 비용은 미확정이며 별도 승인된 성능 측정 후 자원 예산을 정한다.
- 공개: 결과 열람은 별도 승인으로 1회 하며 비공개 채팅 보고가 기본이다. 결과 수치는 PR, 커밋, CI, 공개 문서에 쓰지 않는다. 공개는 별도 결정이다.

## §11 고정과 승인 구조

- 통계 설계 고정: §0–§9, §10의 smoke 규칙, 성능 측정 프로토콜(이름공간 FUTVAL-V8-01-PERF, θ = 0.5와 n 4개 각 rep 0..19의 80복제, M1과 M2의 같은 seed·같은 작업량 비교, 기록 항목, 결과 비기록 조건, W 허용 범위·승인 명시·중단 규칙), 공개 규칙, BASE = 20261118, ε = 1/100은 사용자 승인에 의한 사전등록 고정 커밋으로 확정한다. 고정 뒤 변경은 새 study이며, 성능 측정 실행 뒤에도 이 프로토콜은 바꾸지 않는다.
- 자원 예산: 본 실행 worker 수, wall-clock 상한, 중단 배수는 고정 이후 성능 측정 결과를 보고 별도로 승인한다. 예산 승인이나 예산 부족을 이유로 R, B, 셀, α, ε, λ, 판정 규칙, seed 규칙을 바꾸지 않는다. 예산이 부족하면 실행하지 않거나 새 study로 간다.
- 승인 경계
  - 후보 수락: 사용자
  - 고정 커밋: 사용자 명시 승인. 일반 DELEGATE로 대신하지 않는다
  - 구현·오프라인 테스트·smoke: 해당 Work Order
  - seed 고유성 검사: 통계 계산 전 결정적 사전 검사. 후속 실행 승인에 명시적으로 포함할 수 있다
  - 성능 측정: 별도 실행 승인(W 명시)
  - 자원 예산: 별도 승인
  - 본 실행: 별도 1회 승인
  - 결과 열람: 별도 1회 승인
  - 결과 공개: 별도 결정
