# MoneyLab Architecture

This document describes the architecture that exists in the repository today and how mature each part is. It is
derived from the code, its import graph and the tests that enforce the dependency rules. Planned work is listed
separately and is not implemented.

> **Research stage. No live trading.** Order placement, wallet connection, private-key use, automated trading and
> real-money execution are not implemented. Backtest results so far are synthetic (`SYNTHETIC / NOT_EVIDENCE`).
> Nothing here is evidence of profitability.

Status labels used below:

| Label | Meaning |
|---|---|
| `IMPLEMENTED` | Working code with offline tests. |
| `PARTIAL / SYNTHETIC-ONLY` | Working code, exercised only on synthetic or fixture data so far. |
| `DESIGN_ONLY / INTERFACE_ONLY` | A design document or an abstract interface; no working implementation. |
| `NOT_IMPLEMENTED` | Does not exist in the repository. |

## 1. System Overview

MoneyLab is a Python quantitative research and backtesting platform. Its purpose is to test, under preregistered
rules, whether simple market strategies keep an edge after transaction costs, and to report a negative answer as
readily as a positive one.

Current scope:

- read-only market data access (Upbit public REST/WebSocket; Polymarket public API through synthetic fixtures),
  recording and deterministic replay;
- an offline, cost-aware backtest engine with verification and reporting, run on synthetic fixture data;
- a research layer: the v0.4 microstructure study pipeline and the MC-V06 Monte Carlo study of the v0.6 decision
  procedures;
- evidence labels, integrity hashes and an offline test suite in CI.

There is no live order path. `execution` defines an interface only.

## 2. Design Principles

- **Provider-neutral core.** Analysis code depends on `domain` types and on the abstract interfaces in
  `providers.base`, never on a concrete provider. Enforced by `tests/test_architecture_and_cli.py`.
- **Isolated backtest engine.** `backtest` (and `domain/bars.py`) must not import providers, research, paper, pnl,
  sizing, strategy, execution or network/subprocess modules, and `research` must not import `backtest`. Enforced
  by `tests/test_backtest_architecture.py`.
- **Net, not gross.** Fees, spread and slippage are subtracted before any decision; until the account fee is
  confirmed, the most expensive scenario (25 bp) is the default.
- **Preregistration and locked data.** Hypotheses, thresholds and splits are fixed before data is examined; test
  splits and holdout / forward vaults refuse re-opening.
- **Evidence labels.** Outputs carry labels such as `SYNTHETIC / NOT_EVIDENCE` or `NEGATIVE_EVIDENCE`, so
  synthetic or under-powered results are not reported as findings.
- **Integrity by default.** Raw data and run outputs are written atomically, hashed (SHA-256) and verified by
  separate read-only commands; runs never overwrite earlier outputs.
- **Fail visibly.** Provider errors are returned as diagnostics; HTTP 451/401/403 are not retried; access
  restrictions are not bypassed.

## 3. Component Architecture

```
                         cli (python -m moneylab ...)
                                   |
     +-------------+---------------+----------------+--------------+
     |             |               |                |              |
  scanner     paper / strategy   backtest        research      providers
     |        risk / sizing / pnl   |               |          (polymarket, upbit)
     |             |               |               |              |
     |             |      analytics, storage   analytics,         +--> recording
     |             |               |           storage            +--> paper (replay stream)
     v             v               v               v              v
  providers.base (interfaces)    domain (provider-neutral types)   core (http, errors,
                                                                   redaction, logging)
```

Arrows point from importer to imported package. `backtest` imports only `analytics`, `domain` and `storage`.

| Component | Package | Status | Notes |
|---|---|---|---|
| Core utilities | `core/` | `IMPLEMENTED` | HTTP client (timeout, retry, diagnostics), errors, secret redaction, logging. |
| Domain types | `domain/` | `IMPLEMENTED` | Markets, order books, trades, bars, events. No dependencies inside MoneyLab. |
| Storage | `storage/` | `IMPLEMENTED` | Atomic writes, raw / processed storage. |
| Upbit provider | `providers/upbit/` | `IMPLEMENTED` | Public REST candles and public WebSocket recorder; public market data only. |
| Polymarket provider | `providers/polymarket/` | `PARTIAL / SYNTHETIC-ONLY` | Real access returned HTTP 451 (error category "legal") in the development environment; the cause was not determined. Behaviour is verified on fixtures written from the official documentation. This is not real-market validation. |
| Recording / replay | `recording/`, `providers/*/recorder` | `IMPLEMENTED` | Shared recorder core, checksums, integrity verification, deterministic replay. |
| Scanner | `scanner/` | `PARTIAL / SYNTHETIC-ONLY` | Polymarket market scanner; exercised on fixtures. |
| Offline order-book simulation | `paper/`, `strategy/`, `risk/`, `sizing/`, `pnl/` | `PARTIAL / SYNTHETIC-ONLY` | Offline simulation of quoting strategies on fixtures and recordings. Not paper trading against a live venue. |
| Analytics | `analytics/` | `IMPLEMENTED` | Metrics, expected value, spot cost models. |
| Backtest engine | `backtest/` | `PARTIAL / SYNTHETIC-ONLY` | BT-1 to BT-3e: bars, cost model, fills, ledger, metrics, reports, evaluation boundaries, input identity, holdout / forward vault, monthly forward risk check. Tested on synthetic data only. |
| v0.4 research pipeline | `research/` | `IMPLEMENTED` | As-of features, labels, time-ordered splits with a test lock, statistics. Applied to one real Upbit session; decision REJECT. |
| MC-V06 Monte Carlo study | `research/v06/` | `IMPLEMENTED` | Synthetic data generating processes, v0.6 procedures, operating-characteristic study. Complete; result MIXED / DESIGN-INFORMATIVE. |
| Execution | `execution/` | `DESIGN_ONLY / INTERFACE_ONLY` | Abstract order / fill types (2 files, 77 lines). Design: `docs/live_execution_design.md`. |
| Live trading | - | `NOT_IMPLEMENTED` | No order placement, wallet or key handling. |

## 4. Backtest Data Flow

The offline pipeline, as run by `examples/synthetic_backtest_demo.py`:

```
tests/fixtures/upbit_candles_backtest_synthetic.json   (synthetic linear prices, meta.synthetic = true)
        |
        |  candles-pull --source fixture   (scripted session, no network)
        v
  candle pull dir: pages/NNNN.json + pull.json  (SHA-256 per page; candles-verify replays it)
        |
        |  bars-export   (fixture provenance only; output root must end in -fixture)
        v
  bars dir: bars_<interval>.jsonl + bars_manifest.json (bars_sha256) + SHA256SUMS.txt
        |
        |  backtest --rule sma20 --scenario E0 --fee-bps 25 --settings configs/backtest_costs.toml
        v
  run dir: daily.jsonl, orders.jsonl, trades.jsonl, metrics.json, result.json,
           manifest.json (code state, input identity, result_sha256), SHA256SUMS.txt
        |
        |  backtest-verify   (read-only: files, inputs, identity, settings, code, reproducibility,
        |                     accounting, boundary, engine self-check)
        v
  backtest-report --seed --b1-draws   (metrics and benchmarks; only for a verified run)
        |
        v
  backtest-report-verify   (read-only; re-verifies the run as well)
```

Determinism. The bar hashes and the run files `daily.jsonl`, `metrics.json`, `trades.jsonl` and `orders.jsonl`
are identical across independent runs of the same configuration. The existing result integrity hash
(`result_sha256`) includes timestamp-bearing provenance (pull and bar directory names) and is therefore not a
cross-run deterministic identifier; it is a per-run integrity value that `backtest-verify` checks.

Code state. Every run records the Git commit and a classified working tree (`backtest/code_state.py`). Verification
fails its `code` check if tracked files changed or execution-relevant untracked files exist, and reports are only
built for runs that verify. A clean Git checkout with an editable install is therefore required for the full
pipeline.

## 5. Research / Evidence Flow

```
preregistration (docs/, configs/)  --SHA-256 pinned-->  study pipeline
        |                                                     |
        |                                    train / validation statistics
        |                                                     |
        +------------------------------------> test split opened once (research-final)
                                                              |
                                                     labelled decision
                         (e.g. NEGATIVE_EVIDENCE, RESEARCH_MORE, PAPER_CANDIDATE, REJECT)

procedure validation:  synthetic DGPs --> v0.6 procedures --> Monte Carlo operating characteristics (MC-V06)
```

Research status:

| Item | Status |
|---|---|
| v0.4 real-data microstructure study (Upbit KRW-BTC, one 6-hour session) | **REJECT** after costs: predicted moves far smaller than round-trip costs. |
| Backtest BT-1 to BT-3e | Implemented; results on synthetic data only, `SYNTHETIC / NOT_EVIDENCE`. |
| MC-V06 | Complete. **MIXED / DESIGN-INFORMATIVE.** The futility procedure was anti-conservative at the boundary (rejected more often than nominal) in the synthetic settings; the cause is unresolved, so its validity remains open. |
| BT4 | **Design only** (BT4-DESIGN-01). Its readiness label READY_WITH_CAUTION refers to proceeding with that design work, not to live-trading readiness. No BT4 freeze, validation or implementation has been performed. |
| v0.6 preregistration | Draft, not frozen. |
| BT-5 (real-data backtest), BT-6 (forward evaluation) | Not started. |
| Live trading | Not implemented. |

## 6. Quality & Reproducibility Controls

| Control | Where |
|---|---|
| Offline test suite (no network by default; `-m network` is opt-in) | `tests/`, `pyproject.toml` |
| Dependency-boundary tests | `tests/test_architecture_and_cli.py`, `tests/test_backtest_architecture.py` |
| Repository hygiene test (secrets, personal paths) | `tests/test_repo_hygiene.py` |
| Lint (ruff, rule set `E4,E7,E9,F`) and scoped type check (mypy on `execution`, `pnl`, `scanner`, `sizing`) | Windows CI job, `pyproject.toml` |
| Branch coverage measured (no threshold) | Windows CI job |
| Experimental Linux job (non-blocking) | `.github/workflows/ci-tests.yml` |
| Pinned requirements, deterministic seeds | `requirements*.txt`, seeded procedures |
| Atomic writes, SHA-256 manifests, read-only verify commands | `storage/atomic.py`, `*-verify` commands |
| Code-state pinning of backtest runs | `backtest/code_state.py` |
| Development process: fail-closed agent guard, immutable Work Orders with ERRATA, human authorization gates | `.claude/`, `docs/tasks/`, `docs/agent_workflow.md` |

The development-process controls govern how changes are made; they are not runtime components.

## 7. Repository Structure

```
src/moneylab/
  cli.py, __main__.py   CLI entry point
  core/                 HTTP client, errors, redaction, logging
  domain/               provider-neutral types
  providers/            polymarket/, upbit/ clients, parsers, recorders, candle collection
  recording/            shared recorder core
  storage/              atomic writes, raw / processed storage
  analytics/            metrics and cost models
  backtest/             backtest engine, reports, segments, vault, risk check
  research/             v0.4 pipeline; v06/ Monte Carlo study
  strategy/, risk/, sizing/, paper/, pnl/, scanner/, display/
  execution/            interface only
examples/               synthetic_backtest_demo.py (offline pipeline demonstration)
tests/                  offline tests; synthetic fixtures (provenance in tests/fixtures/README.md)
configs/                backtest cost settings, preregistered study configuration
docs/                   design, preregistration, evidence review, Work Orders
```

## 8. Current Boundaries / Non-Goals

Current boundaries:

- No live trading, order placement, wallet connection or private-key handling.
- No real-data backtest yet; all backtest evidence is synthetic.
- Polymarket is fixture-only (HTTP 451 in the development environment). No access-restriction bypass is
  implemented, by design.
- Account fees are unconfirmed; decisions use a conservative 25 bp assumption.
- The v0.6 statistical procedures are still being validated, and the v0.6 preregistration is not frozen.

Planned / future (`NOT_IMPLEMENTED`; nothing below exists in the repository):

- a knowledge / context layer;
- a policy and risk engine;
- worker agents and tools;
- a supervisor and task generation;
- an autonomous research loop;
- paper trading against a live venue before any live-readiness work;
- human capital and risk approval gates for any real-money step.

## 9. Known Documentation Discrepancies

Recorded here without changing the other documents:

1. The README architecture diagram groups `backtest` with `strategy`, `risk`, `paper`, `research` and `analytics`
   as `domain` consumers. It does not show the enforced backtest boundary: `backtest` may import only `analytics`,
   `domain` and `storage`, and has its own strategy rules, cost model and metrics.
2. `CLAUDE.md` states that profitability metrics are computed in `analytics/metrics.py` and shared by backtest,
   paper and live. In the code, `backtest/metrics.py` computes the backtest metrics and reuses only
   `analytics.metrics.max_drawdown`; there is no live path. The sharing is partial.
3. `risk` and `strategy` import each other (`risk` uses `strategy.base.Signal`; `strategy` uses
   `risk.inventory.reservation_price`).
4. `providers` imports `paper`: the Upbit recorder verification replays order books through
   `paper.book_stream.ReplayBookStream`, while `paper` imports `providers.base`.
