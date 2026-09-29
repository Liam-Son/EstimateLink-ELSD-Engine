# Estimate-Link × Certainty × IV180 Sector Hybrid — Engine v3.0

Research-hardened implementation of submitted BRAIN alpha `levWKewl` plus a guarded IBKR **paper** adapter.

The submitted Fast Expression and BRAIN settings remain unchanged in `brain_alpha.json`. v3.0 does **not** retune the alpha weights/lookbacks.

## Run the full test suite

```powershell
python -m unittest discover -s tests -v
```

## Synthetic plumbing test

```powershell
python make_sample.py --output sample.csv --names 80 --days 320
python engine.py --input sample.csv --output results
```

Synthetic output is wiring evidence only, never financial evidence.

## Real research panel

```powershell
python engine.py --input your_point_in_time_panel.csv --output results --os-start 2024-01-01
```

Required columns:

`date,ticker,sector,industry,open,high,low,close,volume,est_ptp,est_fcf,est_eps,earnings_certainty_rank_derivative,implied_volatility_call_180,implied_volatility_put_180`

Recommended optional columns:

- `adv20` — licensed/point-in-time equivalent of BRAIN ADV20. `auto` prefers it.
- `return_1d` — realized total return for the row's day. If absent, the engine uses close-to-close price return.

Use survivorship-bias-free point-in-time universe membership, classifications, estimates and option data. Corporate actions/delistings must be represented in the return data; strict mode deliberately stops instead of silently dropping held names with missing realized returns.

## Main outputs

- `signals.csv` — final alpha and neutral/capped target weights.
- `components.csv` — all factor sleeves + data ages.
- `backtest.csv` — daily gross/net PnL, costs, turnover and concentration.
- `report.json` — headline metrics, yearly metrics, IS/OS split, Spearman IC, block bootstrap, cost stress and capacity diagnostics.
- `ablation.json` — link/certainty/IV/core/range/pre-decay/final attribution without parameter tuning.
- `data_quality.json` — input and signal quality diagnostics.
- Estimate/IV age fields measure **consecutive missing observations**, not vendor publication age. Repeated stale values cannot be identified without source as-of timestamps.
- `run_manifest.json` — SHA-256 hashes and run settings for reproducibility.

## Timing

Default remains deliberately conservative and compatible with v2:

signal after close `t` → one-day delay → position earns close `t+1` to close `t+2`.

Exact BRAIN Delay semantics are proprietary; offline equivalence is not claimed.

## Gap handling

v3 defaults to `gap_policy=reset`: if a ticker disappears from the panel and later reappears, its time-series histories and `trade_when` state reset. This prevents the old engine from silently compressing missing trading dates and reviving stale held state.

Legacy compression exists only for comparison:

```powershell
python engine.py --input data.csv --output legacy_gap_test --gap-policy compress
```

## IBKR paper trading

Install optional dependency. For the IBKR adapter, **Python 3.13 is currently the conservative choice**; an upstream `ib_async` issue remains open for Python 3.14 event-loop compatibility as of September 2026.

```powershell
pip install -r requirements.txt
```

Read-only delta-order preview:

```powershell
python ibkr_paper.py --signals results/signals.csv --host 127.0.0.1 --port 7497 --account YOUR_PAPER_ACCOUNT
```

Unlike v2, orders are **deltas versus current IBKR positions**, not full target positions. A persistent `estimate_link_paper_state.json` tracks only strategy-managed symbols, so disappeared targets can be closed without touching unrelated account holdings. Preview mode does not mutate this state.

Actual **paper-account** order submission is disabled unless every guard is explicitly supplied:

```powershell
python ibkr_paper.py --signals results/signals.csv --host 127.0.0.1 --port 7497 --account YOUR_PAPER_ACCOUNT --execute-paper --ack PAPER_ONLY
```

The adapter refuses non-paper default ports, requires an explicit account for execution, checks signal age, gross/name/order limits, blocks partial execution when any required quote/risk check fails, refuses a new rebalance while prior strategy orders remain open, and emits borrow-check flags for target shorts. Before execution, independently verify that the connected TWS/Gateway session is your paper account; port gating cannot prove account type.

## What this still cannot make "perfect"

Exact BRAIN rank/pasteurization/NaN/truncation/universe semantics are proprietary. A real production test also requires licensed point-in-time estimate/options data, corporate-action/delisting returns, borrow availability/fees, and realistic venue-specific execution/slippage. v3 fails closed on many of these instead of inventing them.
