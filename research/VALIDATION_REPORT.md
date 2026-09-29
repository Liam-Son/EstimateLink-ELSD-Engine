# Validation Report — v3.0

## Release checks completed

- Python source compilation: PASS.
- Unit/integration tests: **14/14 PASS**.
- Randomized portfolio constraint sweep: PASS.
- Missing-observation/re-entry state test: PASS.
- IBKR target-vs-current delta sizing test: PASS.
- Removed managed symbol liquidation-plan test: PASS.
- Paper execution preflight blocker test: PASS.
- End-to-end synthetic plumbing run: PASS; all expected outputs generated.
- Zip integrity test: PASS.

## Alpha-drift check

On the same deterministic, gap-free 80-name × 320-day panel, v2.0 and v3.0 produced:

- overlapping finite raw signals: **18,400**
- maximum absolute raw-signal difference: **0.0**
- nonzero differences above 1e-12: **0**

This confirms the v3 hardening did not alter the submitted signal calculation on the comparable baseline path. Portfolio construction and diagnostics were intentionally hardened separately.

## Synthetic performance warning

The synthetic panel exists only to exercise wiring, warm-up, missingness and execution plumbing. Any Sharpe, return, drawdown, IC or ablation statistic produced from that panel is deliberately **not** treated as financial evidence.

## Remaining validation that requires external systems/data

- exact WorldQuant BRAIN proprietary operator/pasteurization/NaN/universe equivalence
- licensed survivorship-bias-free point-in-time estimates and IV180 history
- corporate-action and delisting total returns
- actual short availability and borrow fees
- real bid/ask spread, impact and venue execution
- an authenticated IBKR paper session for runtime execution testing
