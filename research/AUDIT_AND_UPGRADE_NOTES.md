# v3.0 audit and upgrade notes

## Material issues found in v2.0

1. **Time compression on missing observations.** Per-name histories only advanced when a ticker row existed. A ticker disappearing and returning could therefore stitch old and new observations together as if no days had elapsed. `trade_when` state could also revive after the gap. v3 defaults to resetting history/state on re-entry.
2. **IBKR preview used full target quantities, not delta-to-current-position quantities.** This could imply repeated buys/sells of the full target. v3 reconciles against current account positions.
3. **Portfolio allocator could violate neutrality when gross target was infeasible under cap/name constraints.** v3 uses side-balanced capped water filling; infeasible books remain neutral and under-invested rather than violating constraints.
4. **Held rows with invalid/NaN prices could be dropped even when missing-row policy was strict.** v3 fails on missing realized returns in strict mode and supports optional `return_1d`.
5. **Only four tests existed.** v3 expands operator, gap, portfolio fuzz, backtest and IBKR-delta tests.

## Additional hardening

- strict ISO date and OHLC/group/volume validation
- input/config/alpha SHA-256 manifest
- staleness-age diagnostics for estimates and IV
- ADV20 source diagnostics
- component ablation without alpha retuning
- cross-sectional Spearman IC / IC IR
- yearly and optional IS/OS metrics
- deterministic block bootstrap
- 0/5/10/20/50 bps cost stress
- concentration, max-weight, turnover, exposure and capacity diagnostics
- optional daily borrow/financing cost terms
- guarded paper execution with read-only preview as default

## Deliberately unchanged

- submitted alpha expression
- signal weights and lookbacks
- BRAIN metadata and ID `levWKewl`
- platform Decay=5 approximation

## Irreducible external limitations

No offline clone can prove exact BRAIN equivalence without the platform's proprietary operator semantics and point-in-time datasets. No backtest can establish live profitability. The engine therefore reports approximation and data limitations rather than filling them with assumptions.

## Second-pass findings fixed before release

- Maximum drawdown now measures from initial equity 1.0, so an immediate first-period loss is not ignored.
- Report now includes active-period metrics separately from calendar-inclusive warm-up metrics.
- Paper adapter persists strategy-managed symbols and creates zero targets for removed names, while leaving unrelated account positions alone.
- Paper execution is all-or-nothing on quote/order-limit preflight and refuses overlapping strategy orders.
- Run manifest now hashes the engine source files in addition to input/config/alpha metadata.
- `ib_async` dependency is moved to the maintained 2.1.x line; Python 3.13 is recommended for the adapter while the upstream Python 3.14 event-loop issue remains open.
