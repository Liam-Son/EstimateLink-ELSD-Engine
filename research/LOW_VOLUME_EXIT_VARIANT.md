# Estimate-Link low-volume exit variant

Paste `EstimateLink_low_volume_exit_FASTEXPR.txt` into a **new** WorldQuant BRAIN alpha. Keep the existing `levWKewl` alpha as the baseline.

The only expression change is the third argument of `trade_when`:

```text
0  →  volume < 0.50*adv20
```

The range sleeve now clears its held value when daily volume falls below half its 20-day average. It still updates on `volume > 0.85*adv20`. This is a hypothesis about stale held signals, not a tested performance improvement.

Use the baseline settings for a like-for-like comparison: Equity; USA; TOP3000; Delay 1; Decay 5; Market neutralization; Truncation 0.06; Pasteurization On; NaN handling Off; Unit handling Verify; Max Trade Off; Max Position Off; 2019-01-01 through 2023-12-31.

The corresponding offline engine settings are in `config_low_volume_exit.json`. Run them only with licensed point-in-time estimate and 180-day options data. No real-data backtest was run for this variant.
