"""Estimate-Link v3 research engine with a separate TOP3000 universe check.

Provide a licensed, point-in-time panel CSV in the project root or Object Store. All factor calculations use
only each row's date and earlier rows. The backtest never uses a same-day signal.
"""
from AlgorithmImports import *
from datetime import date
from bisect import bisect_left
from collections import deque
from pathlib import Path
import math

from data_layer import load_panel, SIGNAL_FIELDS
from signal_engine import compute
from portfolio import weights
from operators import ok
from config_values import CONFIG


class RollingLiquidityTop3000:
    """Rank the available US stocks by trailing 63-day average dollar volume."""

    def __init__(self, lookback=63, count=3000):
        self.lookback = lookback
        self.count = count
        self.day = 0
        self.history = {}
        self.totals = {}
        self.last_seen = {}

    def select(self, fundamentals):
        self.day += 1
        ranked = []
        seen = set()
        for f in fundamentals:
            if not f.has_fundamental_data or f.price <= 0 or f.dollar_volume <= 0:
                continue
            symbol = f.symbol
            if symbol in seen:
                continue
            seen.add(symbol)
            values = self.history.setdefault(symbol, deque())
            total = self.totals.get(symbol, 0.0)
            if len(values) == self.lookback:
                total -= values.popleft()
            value = float(f.dollar_volume)
            values.append(value)
            total += value
            self.totals[symbol] = total
            self.last_seen[symbol] = self.day
            ranked.append((total / len(values), symbol))
        if self.day % 20 == 0:
            stale = [s for s, seen in self.last_seen.items() if self.day - seen > self.lookback]
            for symbol in stale:
                del self.history[symbol]
                del self.totals[symbol]
                del self.last_seen[symbol]
        ranked.sort(key=lambda item: item[0], reverse=True)
        top = ranked[:self.count]
        return ({symbol for _, symbol in top}, len(ranked),
                [symbol.value for _, symbol in top[:10]],
                [symbol.value for _, symbol in top[-10:]],
                top[-1][0] if top else 0.0)


class EstimateLinkResearch(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2019, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(1000000)
        self.set_time_zone("America/New_York")
        if self.live_mode:
            raise RuntimeError("Live deployment is disabled. This algorithm is backtest-only.")
        self.spy = self.add_equity("SPY", Resolution.DAILY).symbol
        self._allow_orders = self.get_parameter("backtest_orders", "false").lower() == "true"
        self._universe_only = self.get_parameter("universe_only", "true").lower() == "true"
        if self._universe_only:
            if self._allow_orders:
                raise RuntimeError("universe_only has no alpha signal and cannot place orders")
            self._liquidity = RollingLiquidityTop3000()
            self._universe_days = 0
            self._last_report_month = None
            self._last_month_members = None
            self._min_eligible = float("inf")
            self._max_eligible = 0
            self._min_selected = float("inf")
            self._max_selected = 0
            self._year_samples = {}
            self.universe_settings.resolution = Resolution.DAILY
            self.add_universe(self._select_top3000)
            self.log("TOP3000 UNIVERSE CHECK ONLY, 2019-2023: Morningstar-covered US stocks "
                     "ranked by 63-day average dollar volume; first 63 days build history; no orders")
            return
        local_name = self.get_parameter("panel_file", "top3000_panel.csv")
        if Path(local_name).name != local_name:
            raise RuntimeError("panel_file must be a filename in the project root")
        panel_path = Path(__file__).with_name(local_name)
        if not panel_path.is_file():
            key = self.get_parameter("panel_key", "")
            if not key or not self.object_store.contains_key(key):
                raise RuntimeError(f"Missing project file {local_name}; no Object Store fallback key")
            panel_path = Path(self.object_store.get_file_path(key))
        cfg = CONFIG
        dates, quality = load_panel(panel_path, strict=True)
        if sum(day < "2019-01-01" for day in dates) < cfg["timing"]["warmup_days_recommended"]:
            raise RuntimeError("Panel needs at least 200 trading days before 2019 for signal warm-up")
        if not any("2019-01-01" <= day <= "2023-12-31" for day in dates):
            raise RuntimeError("Panel has no observations in the 2019-2023 test window")
        if quality["min_names_per_day"] < cfg["portfolio"]["min_names"]:
            raise RuntimeError("Panel has too few names on one or more days")
        # The original v3 computations, unchanged. No synthetic fallback for absent fields.
        self._signals, _, diagnostic = compute(
            dates, cfg, adv20_mode=cfg["research"]["adv20_mode"],
            gap_policy=cfg["research"]["gap_policy"], include_components=False)
        self._dates = sorted(self._signals)
        self._cfg = cfg
        self._last_signal = None
        self._managed = set()
        self.log(f"Panel {quality['rows']} rows; SHA256 {quality['input_sha256']}; "
                 f"signals {len(self._dates)} days; orders {'ON' if self._allow_orders else 'OFF'}")

    def _select_top3000(self, fundamentals):
        members, eligible, leaders, boundary, cutoff = self._liquidity.select(fundamentals)
        self._universe_days += 1
        self._min_eligible = min(self._min_eligible, eligible)
        self._max_eligible = max(self._max_eligible, eligible)
        self._min_selected = min(self._min_selected, len(members))
        self._max_selected = max(self._max_selected, len(members))
        self._year_samples[self.time.year] = (
            self.time.date(), len(members), eligible, leaders, boundary, cutoff)
        month = (self.time.year, self.time.month)
        if month != self._last_report_month:
            retained = (len(members & self._last_month_members)
                        if self._last_month_members is not None else 0)
            self.log(f"{self.time.date()}: {len(members)}/{eligible} stocks; "
                     f"month-over-month retained {retained}; cutoff ADV63 ${cutoff:,.0f}; "
                     f"top10 {','.join(leaders)}; boundary10 {','.join(boundary)}")
            self._last_report_month = month
            self._last_month_members = members.copy()
            self.plot("TOP3000 Universe", "Selected", len(members))
            self.plot("TOP3000 Universe", "Eligible covered stocks", eligible)
        # Keep membership in memory for a later point-in-time signal join. Returning no
        # securities prevents roughly 3,000 daily subscriptions on a Free backtest node.
        self._top3000_today = members
        return []

    def on_data(self, data: Slice):
        if self._universe_only:
            return
        today = self.time.date().isoformat()
        i = bisect_left(self._dates, today) - 1  # strict prior trading day, never today
        if i < 0:
            return
        signal_day = self._dates[i]
        if signal_day == self._last_signal:
            return
        age = (self.time.date() - date.fromisoformat(signal_day)).days
        if age > 4:  # holiday/weekend allowance, otherwise stale
            self.error(f"Stale signal {signal_day}, age {age}; no rebalance")
            return
        pc = self._cfg["portfolio"]
        raw = self._signals[signal_day]
        # Do not renormalize a partially missing factor universe into an artificial book.
        valid = {k: v for k, v in raw.items() if ok(v)}
        if len(valid) < pc["min_names"] or len(valid) < 0.8 * len(raw):
            self.error(f"Incomplete signal {signal_day}: {len(valid)}/{len(raw)} valid")
            return
        target = weights(valid, cap=pc["max_abs_weight"], gross_target=pc["gross_target"])
        target = {k: v for k, v in target.items() if abs(v) > 1e-9}
        if len(target) < pc["min_names"]:
            self.error(f"Too few tradable targets on {signal_day}")
            return
        if any(not math.isfinite(v) or abs(v) > pc["max_abs_weight"] + 1e-9 for v in target.values()):
            raise RuntimeError("Invalid weight or per-name cap")
        if sum(abs(v) for v in target.values()) > pc["gross_target"] + 1e-8 or abs(sum(target.values())) > 1e-8:
            raise RuntimeError("Gross or market-neutrality breach")
        self.log(f"{signal_day}: {len(target)} targets, gross {sum(map(abs, target.values())):.3f}")
        if not self._allow_orders:
            self._last_signal = signal_day
            return
        symbols = {}
        for ticker in set(target) | self._managed:
            symbols[ticker] = self.add_equity(ticker, Resolution.DAILY).symbol
        if any(not self.securities[symbols[k]].has_data or self.securities[symbols[k]].price <= 0
               for k in target):
            self.error(f"Missing LEAN price on {signal_day}; no partial rebalance")
            return
        targets = [PortfolioTarget(symbols[k], float(v)) for k, v in target.items()]
        targets += [PortfolioTarget(symbols[k], 0) for k in self._managed - set(target)]
        self.set_holdings(targets)
        self._managed = set(target)
        self._last_signal = signal_day

    def on_end_of_algorithm(self):
        if self._universe_only:
            self.set_runtime_statistic("QC universe days", str(self._universe_days))
            self.set_runtime_statistic(
                "QC selected min-max", f"{self._min_selected}-{self._max_selected}")
            self.set_runtime_statistic(
                "QC eligible min-max", f"{self._min_eligible}-{self._max_eligible}")
            for year, (day, selected, eligible, leaders, boundary, cutoff) in sorted(
                    self._year_samples.items()):
                self.set_runtime_statistic(
                    f"QC {year} year-end", f"{day}: {selected}/{eligible}")
                self.set_runtime_statistic(f"QC {year} top10", ",".join(leaders))
                self.set_runtime_statistic(
                    f"QC {year} cutoff ADV63", f"${cutoff:,.0f}")
            if self._year_samples:
                self.set_runtime_statistic(
                    "QC 2023 boundary10", ",".join(self._year_samples[max(self._year_samples)][4]))
            self.log(f"TOP3000 universe check complete: {self._universe_days} trading days; "
                     f"eligible stocks ranged {self._min_eligible}-{self._max_eligible}; "
                     "0 alpha trades by design")
