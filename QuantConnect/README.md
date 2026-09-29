# Estimate-Link on QuantConnect LEAN

This project ports the supplied v3 signal and portfolio modules unchanged into a QuantConnect `QCAlgorithm`. It is **backtest-only** and has **orders off by default**. The configured test window is **2019-01-01 through 2023-12-31**, matching the saved BRAIN alpha. It does not claim exact WorldQuant BRAIN semantics or reproduce its TOP3000 result without the required data.

The default `universe_only=true` mode checks a daily TOP3000 approximation using QuantConnect's historical US Equity Coarse Universe. It ranks eligible equities by a rolling 63-trading-day mean of dollar volume and keeps the 3,000 names in memory. It returns no securities from universe selection, avoiding thousands of subscriptions on a Free node. The first 63 days have an incomplete rolling history. This mode makes **zero trades** and produces no Estimate-Link return. It does not fill any missing estimate or IV fields. Set `universe_only=false` only when the licensed panel described below is present.

## Inputs

Add a licensed, point-in-time CSV named `top3000_panel.csv` to the project root (or set the `panel_file` parameter to a different root filename). An optional `panel_key` parameter enables Object Store fallback on plans that support it. The panel needs at least 200 trading days before 2019 for signal warm-up and historical TOP3000 membership, sector, and industry classifications. Required columns:

`date,ticker,sector,industry,open,high,low,close,volume,est_ptp,est_fcf,est_eps,earnings_certainty_rank_derivative,implied_volatility_call_180,implied_volatility_put_180`

The original loader checks duplicate keys and OHLCV validity. The QC adapter requires sufficient valid signals, market neutrality, per-name caps, and a signal from a **prior** date. Use historical TOP3000 membership rather than today's constituents for a historical backtest. The data license must permit use in QuantConnect Cloud. Never populate proprietary fields with made-up values.

## QuantConnect setup

1. In Algorithm Lab, create a Python project and upload `main.py`, `data_layer.py`, `signal_engine.py`, `operators.py`, `portfolio.py`, and `config_values.py` to the same project root. QuantConnect's browser editor did not sync `.json` files; `config.json` and `brain_alpha.json` remain local reference files.
2. Run a single universe-only validation backtest with default settings. It needs no custom panel and places no orders.
3. To evaluate the Estimate-Link signal later, add the validated `top3000_panel.csv` beside `main.py` and set `universe_only=false`. Project storage limits and IDE file-upload support may constrain large historical panels. Object Store is optional, not required for the Free plan.
4. First keep `backtest_orders=false`, which calculates and logs target counts/gross without orders. Only after checking logs should `backtest_orders=true` be used for a separate historical simulated-order backtest. The algorithm explicitly rejects `live_mode`; it cannot be deployed to IBKR through QuantConnect without a separate review and code change.

## Why data is still required

QuantConnect's US Equity Option Universe includes daily contract IV/Greeks and Estimize includes EPS estimates, but these do not automatically give the exact BRAIN `est_ptp`, `est_fcf`, `earnings_certainty_rank_derivative`, or the same definition of 180-day call/put IV. The project CSV is the explicit adapter boundary for licensed, point-in-time values. No panel was supplied in the handoff. A full TOP3000 panel may exceed the QuantConnect Free node's memory even with orders off; no-order mode avoids thousands of equity subscriptions but still loads and computes the panel.

## Validation status

The original v3 unit suite passed 14/14 locally on Python 3.13. The LEAN Python files and rolling-liquidity ranking passed local syntax and smoke checks. The separate [QuantConnect research project](https://www.quantconnect.com/project/37111273) contains the adapter and built successfully. Its universe-only backtest `Adaptable Apricot Cormorant` (ID `cabb82312880408b1f9c20416ece793b`) completed for 2019–2023, processing 11,414,628 data points with zero orders and zero return by design. No Estimate-Link signal backtest was run because the required panel is absent. The older price/volume proxy remains in project `37108490`.
