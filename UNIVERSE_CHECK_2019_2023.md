# QuantConnect TOP3000 universe check, 2019–2023

Final private QuantConnect backtest: `5a5d3a27fbe8ad66094cd65d379fa4b0` in [project 37111273](https://www.quantconnect.com/project/37111273), named **Retrospective Tan kitten**. It completed on LEAN 2.5.0.0.18134, processing 11,414,628 data points in 143.17 seconds. There were no orders and the 0% return is by design: this run selected a universe only and did not calculate or trade the Estimate-Link alpha.

The algorithm ranked unique Morningstar-covered US equity symbols by their trailing 63 observed days of dollar volume. The first 63 dates build history. It selected 3,000 unique symbols on every one of the 1,259 dates. The number of eligible symbols across the run ranged from 3,972 to 5,150.

| QC year-end timestamp | Selected / eligible | Ten highest-liquidity symbols | ADV63 at rank 3,000 |
| --- | ---: | --- | ---: |
| 2019-12-31 | 3,000 / 4,040 | AAPL, AMZN, TSLA, MSFT, ROKU, FB, NFLX, AMD, BA, NVDA | $750,732 |
| 2020-12-31 | 3,000 / 4,320 | TSLA, AMZN, AAPL, MSFT, FB, NVDA, BA, AMD, ZM, GOOGL | $1,866,463 |
| 2021-12-31 | 3,000 / 5,019 | TSLA, AAPL, NVDA, AMZN, MSFT, AMD, FB, GOOGL, MRNA, RIVN | $3,306,199 |
| 2022-12-31 | 3,000 / 4,982 | TSLA, AAPL, AMZN, NVDA, MSFT, AMD, META, NFLX, GOOGL, GOOG | $1,554,667 |
| 2023-12-30 | 3,000 / 4,774 | TSLA, NVDA, AAPL, MSFT, AMD, AMZN, META, BRK.A, GOOGL, GOOG | $1,432,406 |

This is a methodological approximation, not a measured membership match with WorldQuant BRAIN. [BRAIN's settings documentation](https://platform.worldquantbrain.com/learn/documentation/create-alphas/simulation-settings) defines US TOP3000 by highest average daily dollar volume but does not provide its historical constituent lists or exact lookback. [QuantConnect's documentation](https://www.quantconnect.com/docs/v2/writing-algorithms/universes/equity/fundamental-universes) says its Morningstar fundamental coverage excludes ETFs, ADRs, and OTC stocks but misses some US equities. One 2023 boundary symbol was BIT, which [BlackRock identifies as a closed-end fund](https://www.blackrock.com/us/individual/products/249839/blackrock-multi-sector-income-trust-aggregate-bit). Thus this filter does not yield an operating-company-only universe, and the QC results cannot establish an overlap percentage with BRAIN.
