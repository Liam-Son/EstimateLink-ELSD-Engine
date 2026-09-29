"""Market-neutral portfolio construction with exact side balancing and hard caps."""
from __future__ import annotations
from operators import ok


def _allocate_side(scores, budget, cap, tol=1e-14):
    """Water-fill a positive side budget proportional to positive scores under cap."""
    if budget <= tol or not scores:
        return {k: 0.0 for k in scores}
    out = {k: 0.0 for k in scores}
    free = set(scores)
    remaining = budget
    while free and remaining > tol:
        total_score = sum(max(scores[k], tol) for k in free)
        proposed = {k: remaining*max(scores[k],tol)/total_score for k in free}
        hit = [k for k,v in proposed.items() if v >= cap-tol]
        if not hit:
            for k,v in proposed.items(): out[k] += v
            remaining = 0.0
            break
        for k in hit:
            add = min(cap-out[k], proposed[k])
            out[k] += add
            remaining -= add
            free.remove(k)
        if not free:
            break
    return out


def weights(signal, cap=0.06, gross_target=1.0, require_full_gross=False, tol=1e-12):
    vals = {k:v for k,v in signal.items() if ok(v)}
    if len(vals) < 2 or cap <= 0 or gross_target <= 0:
        return {}
    center = sum(vals.values())/len(vals)
    centered = {k:v-center for k,v in vals.items()}
    long_scores = {k:v for k,v in centered.items() if v > tol}
    short_scores = {k:-v for k,v in centered.items() if v < -tol}
    if not long_scores or not short_scores:
        return {}

    target_side = gross_target/2.0
    feasible_side = min(target_side, cap*len(long_scores), cap*len(short_scores))
    if require_full_gross and feasible_side < target_side-tol:
        raise ValueError(
            f"Portfolio constraints infeasible: need {target_side:.6f} gross per side but cap/name counts allow {feasible_side:.6f}"
        )
    long_alloc = _allocate_side(long_scores, feasible_side, cap)
    short_alloc = _allocate_side(short_scores, feasible_side, cap)
    w = {k: long_alloc.get(k,0.0)-short_alloc.get(k,0.0) for k in vals}
    # Numerical cleanup while preserving neutrality.
    net = sum(w.values())
    if abs(net) > 1e-10:
        raise AssertionError(f"Portfolio allocator lost neutrality: {net}")
    if any(abs(v) > cap+1e-10 for v in w.values()):
        raise AssertionError("Portfolio allocator violated cap")
    return w


def exposure_stats(w):
    if not w:
        return {"gross":0.0,"net":0.0,"max_abs":0.0,"hhi":0.0,"names":0}
    gross = sum(abs(v) for v in w.values())
    return {
        "gross": gross,
        "net": sum(w.values()),
        "max_abs": max(abs(v) for v in w.values()),
        "hhi": sum(v*v for v in w.values()),
        "names": sum(abs(v)>0 for v in w.values()),
    }
