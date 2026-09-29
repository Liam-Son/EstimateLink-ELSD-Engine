"""Input validation, quality diagnostics and point-in-time panel loading."""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from operators import NAN, ok

REQUIRED_FIELDS = (
    "date ticker sector industry open high low close volume est_ptp est_fcf est_eps "
    "earnings_certainty_rank_derivative implied_volatility_call_180 implied_volatility_put_180"
).split()
OPTIONAL_FIELDS = ["adv20", "return_1d"]
SIGNAL_FIELDS = ["est_ptp", "est_fcf", "est_eps", "earnings_certainty_rank_derivative",
                 "implied_volatility_call_180", "implied_volatility_put_180"]


def number(row, key):
    try:
        value = row.get(key, "")
        return float(value) if str(value).strip() else NAN
    except (TypeError, ValueError):
        return NAN


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_panel(path: Path, strict=True):
    dates = defaultdict(dict)
    quality = {
        "rows": 0, "invalid_ohlc": 0, "negative_volume": 0, "blank_group": 0,
        "missing_by_field": Counter(), "adv20_supplied_rows": 0, "return_1d_supplied_rows": 0,
    }
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        missing = sorted(set(REQUIRED_FIELDS)-set(fields))
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(missing))
        for line_no, row in enumerate(reader, start=2):
            quality["rows"] += 1
            raw_date = row["date"].strip()
            ticker = row["ticker"].strip()
            try:
                date_obj = dt.date.fromisoformat(raw_date)
            except ValueError as e:
                raise ValueError(f"Line {line_no}: date must be YYYY-MM-DD, got {raw_date!r}") from e
            date = date_obj.isoformat()
            if not ticker:
                raise ValueError(f"Line {line_no}: blank ticker")
            if ticker in dates[date]:
                raise ValueError(f"Duplicate date/ticker at line {line_no}: {date} {ticker}")
            if not row["sector"].strip() or not row["industry"].strip():
                quality["blank_group"] += 1
                if strict:
                    raise ValueError(f"Line {line_no}: blank sector/industry for {ticker}")

            o, h, l, c, v = [number(row, x) for x in ("open","high","low","close","volume")]
            if all(ok(x) for x in (o,h,l,c)):
                if min(o,h,l,c) <= 0 or h < max(o,c,l) or l > min(o,c,h):
                    quality["invalid_ohlc"] += 1
                    if strict:
                        raise ValueError(f"Line {line_no}: invalid OHLC for {ticker}")
            if ok(v) and v < 0:
                quality["negative_volume"] += 1
                if strict:
                    raise ValueError(f"Line {line_no}: negative volume for {ticker}")
            for field in SIGNAL_FIELDS:
                if not ok(number(row, field)):
                    quality["missing_by_field"][field] += 1
            if ok(number(row, "adv20")):
                quality["adv20_supplied_rows"] += 1
            if ok(number(row, "return_1d")):
                quality["return_1d_supplied_rows"] += 1
            dates[date][ticker] = row

    if not dates:
        raise ValueError("Input panel is empty")
    quality["dates"] = len(dates)
    quality["first_date"] = min(dates)
    quality["last_date"] = max(dates)
    quality["unique_tickers"] = len({k for rows in dates.values() for k in rows})
    quality["min_names_per_day"] = min(len(x) for x in dates.values())
    quality["max_names_per_day"] = max(len(x) for x in dates.values())
    quality["missing_by_field"] = dict(quality["missing_by_field"])
    quality["input_sha256"] = sha256_file(path)
    quality["strict_validation"] = bool(strict)
    return dates, quality


def write_quality(path: Path, quality: dict, extra=None):
    payload = dict(quality)
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
