# v2.0 Upgrade Notes

The original `brain_alpha.json` and signal architecture are preserved. v2.0 focuses on research integrity and paper-trading plumbing rather than retuning the alpha.

## Fixed / strengthened

- Preserves the original Estimate-Link × Certainty × IV180 signal and BRAIN platform-decay approximation.
- `adv20` can now come from an optional point-in-time input column (`--adv20-mode input/auto`) instead of always being reconstructed from share volume.
- Portfolio truncation now iteratively targets **market neutrality + gross exposure + 6% cap** instead of clipping once and leaving an under-invested book.
- Transaction costs now default to **actual traded notional** (`sum(abs(delta weight))`) rather than half-turnover. Legacy v1 behavior remains available with `--cost-convention half_turnover`.
- Missing held names now fail closed by default instead of silently disappearing from PnL. This prevents an easy delisting/missing-return bias. `--missing-held-policy drop` exists only for plumbing tests.
- Adds `components.csv` so link, certainty, IV180, core, range, and final sleeves can be audited separately.
- Adds CAGR, annualized return/volatility, hit rate, total cost, average exposure, names, and turnover diagnostics.
- Adds direct tests for `trade_when` statefulness and capped/neutral portfolio construction.
- Adds `ibkr_paper_preview.py`: read-only, paper-port-only IBKR order preview. It contains **no order submission call**.

## Deliberately NOT changed

- The alpha weights and lookbacks are untouched.
- Rank/tie, group-zscore, pasteurization, truncation, and NaN semantics remain approximations because BRAIN's exact proprietary implementation is not available here.
- No claim is made that offline Sharpe reproduces BRAIN Sharpe.
- No live trading is enabled.
