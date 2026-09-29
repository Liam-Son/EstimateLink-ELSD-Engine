"""Signal computation for levWKewl, preserving the submitted expression constants."""
from __future__ import annotations
from collections import defaultdict, deque
from statistics import mean
from operators import NAN, ok, backfill, corr, decay, tsrank, rank, group, trade_when_step
from data_layer import number


def _age_step(previous_age, value):
    if ok(value):
        return 0
    if previous_age is None:
        return None
    return previous_age + 1


def compute(dates, cfg, adv20_mode="auto", gap_policy="reset", include_components=True):
    sc = cfg["signal"]
    history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=320)))
    held = {}
    last_seen_index = {}
    stale_age = defaultdict(dict)
    signals, components = {}, {}
    diagnostics = {
        "gap_resets": 0, "adv20_input_uses": 0, "adv20_rolling_uses": 0,
        "zero_or_invalid_range_rows": 0, "stale_estimate_age_max": 0,
        "stale_iv_age_max": 0,
    }
    all_days = sorted(dates)

    for day_idx, date in enumerate(all_days):
        rows = dates[date]
        sectors = {k: r["sector"] for k, r in rows.items()}
        industries = {k: r["industry"] for k, r in rows.items()}
        stable, certainty, iv180, ranges, volumes, adv20 = {}, {}, {}, {}, {}, {}
        ages_out = {}

        for k, r in rows.items():
            if k in last_seen_index and last_seen_index[k] != day_idx-1 and gap_policy == "reset":
                history.pop(k, None)
                held.pop(k, None)
                stale_age.pop(k, None)
                diagnostics["gap_resets"] += 1
            last_seen_index[k] = day_idx
            h = history[k]

            est_ages = []
            for field in ("est_ptp","est_fcf","est_eps"):
                raw = number(r, field)
                stale_age[k][field] = _age_step(stale_age[k].get(field), raw)
                if stale_age[k][field] is not None:
                    est_ages.append(stale_age[k][field])
                h[field].append(raw)
                h[field+"_bf"].append(backfill(h[field], sc["est_backfill"]))
            p, f, e = [h[field+"_bf"] for field in ("est_ptp","est_fcf","est_eps")]
            cs = [corr(p,f,sc["corr_window"]), corr(p,e,sc["corr_window"]), corr(f,e,sc["corr_window"])]
            raw_stable = -sum(w*v for w,v in zip((0.4,0.3,0.3),cs)) if all(map(ok,cs)) else NAN
            h["stable"].append(raw_stable)
            stable[k] = decay(h["stable"], sc["stable_decay"])

            cert_raw = number(r,"earnings_certainty_rank_derivative")
            h["certainty"].append(cert_raw)
            certainty[k] = tsrank(h["certainty"], sc["certainty_window"])

            call = number(r,"implied_volatility_call_180")
            put = number(r,"implied_volatility_put_180")
            iv_now = call-put if ok(call) and ok(put) else NAN
            stale_age[k]["iv"] = _age_step(stale_age[k].get("iv"), iv_now)
            h["ivraw"].append(iv_now)
            h["ivbf"].append(backfill(h["ivraw"], sc["iv_backfill"]))
            ivwin = list(h["ivbf"])[-sc["iv_mean"]:]
            iv180[k] = mean(ivwin) if len(ivwin)==sc["iv_mean"] and all(map(ok,ivwin)) else NAN

            o, hi, lo, cl = [number(r,x) for x in ("open","high","low","close")]
            if all(map(ok,(o,hi,lo,cl))) and hi > lo:
                range_raw = (cl-o)/(hi-lo)
            else:
                range_raw = NAN
                diagnostics["zero_or_invalid_range_rows"] += 1
            h["range"].append(range_raw)
            ranges[k] = decay(h["range"], sc["range_decay"])

            volumes[k] = number(r,"volume")
            h["volume"].append(volumes[k])
            supplied_adv = number(r,"adv20")
            volwin = list(h["volume"])[-20:]
            rolling_adv = mean(volwin) if len(volwin)==20 and all(map(ok,volwin)) else NAN
            if adv20_mode == "input":
                adv20[k] = supplied_adv
                if ok(supplied_adv): diagnostics["adv20_input_uses"] += 1
            elif adv20_mode == "rolling":
                adv20[k] = rolling_adv
                if ok(rolling_adv): diagnostics["adv20_rolling_uses"] += 1
            else:
                if ok(supplied_adv):
                    adv20[k] = supplied_adv; diagnostics["adv20_input_uses"] += 1
                else:
                    adv20[k] = rolling_adv
                    if ok(rolling_adv): diagnostics["adv20_rolling_uses"] += 1

            max_est_age = max(est_ages) if est_ages else None
            iv_age = stale_age[k].get("iv")
            if max_est_age is not None:
                diagnostics["stale_estimate_age_max"] = max(diagnostics["stale_estimate_age_max"], max_est_age)
            if iv_age is not None:
                diagnostics["stale_iv_age_max"] = max(diagnostics["stale_iv_age_max"], iv_age)
            ages_out[k] = (max_est_age, iv_age)

        link = group(stable, sectors, "rank")
        cert = group(certainty, sectors, "rank")
        ivz = group(iv180, sectors, "zscore")
        mixed = {k: sc["link_weight"]*link[k] + sc["certainty_weight"]*cert[k] + sc["iv_weight"]*ivz[k]
                 if all(map(ok,(link[k],cert[k],ivz[k]))) else NAN for k in rows}
        core = group(mixed, sectors, "neutral")

        range_rank = rank(ranges)
        trade = {}
        exit_ratio = sc.get("range_exit_ratio")
        for k in rows:
            entry = ok(volumes[k]) and ok(adv20[k]) and volumes[k] > sc["volume_gate"]*adv20[k]
            alpha = -range_rank[k] if ok(range_rank[k]) else NAN
            exit_cond = (ok(volumes[k]) and ok(adv20[k]) and adv20[k] > 0 and
                         volumes[k] < exit_ratio*adv20[k]) if exit_ratio is not None else False
            held[k] = trade_when_step(entry, alpha, float(exit_cond), held.get(k,NAN))
            trade[k] = held[k]
        rng = group(trade, industries, "neutral")

        result, day_components = {}, {}
        for k in rows:
            h = history[k]
            h["core"].append(core[k])
            core4 = decay(h["core"], sc["core_decay"])
            raw = sc["core_final_weight"]*core4 + sc["range_final_weight"]*rng[k] if ok(core4) and ok(rng[k]) else NAN
            h["final"].append(raw)
            final = decay(h["final"], sc["platform_decay"])
            result[k] = final
            if include_components:
                max_est_age, iv_age = ages_out[k]
                day_components[k] = {
                    "stable": stable[k], "link_alpha": link[k], "certainty": cert[k], "iv180": ivz[k],
                    "core": core[k], "core_decay4": core4, "range_decay5": ranges[k], "rng": rng[k],
                    "pre_platform_decay": raw, "final_signal": final, "adv20_used": adv20[k],
                    "estimate_max_age_obs": max_est_age if max_est_age is not None else NAN,
                    "iv_age_obs": iv_age if iv_age is not None else NAN,
                }
        signals[date] = result
        if include_components:
            components[date] = day_components
    return signals, components, diagnostics
