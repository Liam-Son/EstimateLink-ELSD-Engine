"""Pure operator approximations used by the Estimate-Link engine.

These intentionally stay dependency-free and explicit so BRAIN-approximation
assumptions can be unit-tested. They are not claimed to reproduce proprietary
WorldQuant implementation details exactly.
"""
from __future__ import annotations
import math
from collections import defaultdict
from statistics import mean, pstdev

NAN = float("nan")


def ok(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def full(hist, n):
    x = list(hist)[-n:]
    return x if len(x) == n and all(map(ok, x)) else None


def backfill(hist, n):
    """Return latest finite observation within current + prior n-1 observations."""
    return next((v for v in list(hist)[-n:][::-1] if ok(v)), NAN)


def corr(a, b, n):
    x, y = full(a, n), full(b, n)
    if x is None or y is None:
        return NAN
    mx, my = mean(x), mean(y)
    den = math.sqrt(sum((v-mx)**2 for v in x) * sum((v-my)**2 for v in y))
    return sum((u-mx)*(v-my) for u, v in zip(x, y))/den if den else NAN


def decay(hist, n):
    x = full(hist, n)
    return sum(v*(i+1) for i, v in enumerate(x))/(n*(n+1)/2) if x else NAN


def tsrank(hist, n):
    """Midpoint percentile rank of the latest observation."""
    x = full(hist, n)
    if x is None:
        return NAN
    return (sum(v < x[-1] for v in x) + 0.5*sum(v == x[-1] for v in x))/n


def rank(vals):
    """Midpoint percentile cross-sectional ranks, preserving NaN."""
    ordered = sorted((v, k) for k, v in vals.items() if ok(v))
    result = {k: NAN for k in vals}
    n = len(ordered)
    if not n:
        return result
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        r = (i + j)/(2*n)
        for _, k in ordered[i:j]:
            result[k] = r
        i = j
    return result


def group(vals, labels, mode):
    buckets = defaultdict(dict)
    result = {k: NAN for k in vals}
    for k, v in vals.items():
        label = labels.get(k)
        if label is None or str(label).strip() == "":
            continue
        buckets[label][k] = v
    for entries in buckets.values():
        if mode == "rank":
            result.update(rank(entries))
            continue
        good = [v for v in entries.values() if ok(v)]
        center = mean(good) if good else NAN
        sd = pstdev(good) if len(good) > 1 else 0.0
        for k, v in entries.items():
            if not ok(v):
                result[k] = NAN
            elif mode == "neutral":
                result[k] = v-center
            elif mode == "zscore":
                result[k] = (v-center)/sd if sd else 0.0
            else:
                raise ValueError(f"Unknown group mode: {mode}")
    return result


def trade_when_step(entry, alpha, exit_cond, previous=NAN):
    """Approximate BRAIN trade_when state transition."""
    if ok(exit_cond) and exit_cond > 0:
        return NAN
    if bool(entry):
        return alpha if ok(alpha) else previous
    return previous


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if ok(x) and ok(y)]
    if len(pairs) < 3:
        return NAN
    a, b = zip(*pairs)
    ma, mb = mean(a), mean(b)
    den = math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x, y in pairs)/den if den else NAN


def spearman(vals_a, vals_b):
    keys = [k for k in vals_a if k in vals_b and ok(vals_a[k]) and ok(vals_b[k])]
    if len(keys) < 3:
        return NAN
    ra = rank({k: vals_a[k] for k in keys})
    rb = rank({k: vals_b[k] for k in keys})
    return pearson([ra[k] for k in keys], [rb[k] for k in keys])
