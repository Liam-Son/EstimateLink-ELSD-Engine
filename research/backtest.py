"""Leakage-conscious backtest, diagnostics, ablations, IC and stress tests."""
from __future__ import annotations
import csv
import datetime as dt
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, pstdev
from operators import NAN, ok, spearman
from data_layer import number
from portfolio import weights, exposure_stats


def _metrics(returns, equity_curve):
    if not returns:
        return {k:None for k in ("annualized_return_arithmetic","annualized_volatility","annualized_net_sharpe","cagr","hit_rate","max_drawdown","max_drawdown_duration_days","total_return")}
    ann_ret = mean(returns)*252
    vol_d = pstdev(returns) if len(returns)>1 else 0.0
    ann_vol = vol_d*math.sqrt(252)
    sharpe = mean(returns)/vol_d*math.sqrt(252) if vol_d>0 else None
    years = len(returns)/252
    cagr = equity_curve[-1]**(1/years)-1 if years>0 and equity_curve[-1]>0 else None
    peak = 1.0; max_dd=0.0; cur_dur=0; max_dur=0
    for x in equity_curve:
        if x >= peak:
            peak=x; cur_dur=0
        else:
            cur_dur += 1; max_dur=max(max_dur,cur_dur)
            max_dd=max(max_dd,1-x/peak)
    return {
        "annualized_return_arithmetic":ann_ret,"annualized_volatility":ann_vol,"annualized_net_sharpe":sharpe,
        "cagr":cagr,"hit_rate":sum(r>0 for r in returns)/len(returns),"max_drawdown":max_dd,
        "max_drawdown_duration_days":max_dur,"total_return":equity_curve[-1]-1,
    }


def _realized_return(today_row, yesterday_row):
    supplied = number(today_row,"return_1d")
    if ok(supplied):
        return supplied, "return_1d"
    c1, c0 = number(today_row,"close"), number(yesterday_row,"close")
    if not ok(c1) or not ok(c0) or c0 <= 0:
        return NAN, "missing"
    return c1/c0-1.0, "close_to_close"


def build_targets(signals, cfg, min_names=None):
    pc=cfg["portfolio"]
    min_names = pc["min_names"] if min_names is None else min_names
    targets={}
    meta={}
    for d,sig in signals.items():
        w=weights(sig,cap=pc["max_abs_weight"],gross_target=pc["gross_target"])
        if len([x for x in w.values() if abs(x)>0]) < min_names:
            w={}
        targets[d]=w
        meta[d]=exposure_stats(w)
    return targets,meta


def run_strategy(dates, signals, cfg, *, cost_bps=None, delay_days=None, price_policy="error", output_csv=None):
    rc=cfg["research"]
    delay = cfg["timing"]["delay_days"] if delay_days is None else int(delay_days)
    cost_bps = rc["cost_bps_per_dollar_traded"] if cost_bps is None else float(cost_bps)
    borrow_bps = float(rc.get("short_borrow_bps_annual",0.0))
    financing_bps = float(rc.get("financing_bps_annual",0.0))
    targets, target_meta = build_targets(signals,cfg)
    days=sorted(dates)
    rows_out=[]; returns=[]; eq=[]; equity=1.0; prev={}
    turnovers=[]; costs=[]; names=[]; gross_exps=[]; net_exps=[]; hhis=[]; max_weights=[]
    return_source_counts=defaultdict(int)
    participation=[]; capacity_breaches=0
    capital=float(rc.get("capacity_capital",0.0)); max_part=float(rc.get("max_adv_participation",1.0))

    # signal t with delay=1 earns from close(t+1) to close(t+2), matching v2's conservative clock.
    offset=delay+1
    for i in range(offset,len(days)):
        signal_day=days[i-offset]
        pnl_day=days[i]
        prev_day=days[i-1]
        target=targets.get(signal_day,{})
        today,yesterday=dates[pnl_day],dates[prev_day]

        bad=[]; realized={}
        for k,v in target.items():
            if abs(v)<=0: continue
            if k not in today or k not in yesterday:
                bad.append((k,"missing_row")); continue
            r,src=_realized_return(today[k],yesterday[k])
            if not ok(r): bad.append((k,"missing_return")); continue
            realized[k]=r; return_source_counts[src]+=1
        if bad and price_policy=="error":
            raise ValueError(f"Held names lack realizable return on {pnl_day}: {bad[:8]}")
        live={k:v for k,v in target.items() if k in realized}
        gross_ret=sum(live[k]*realized[k] for k in live)

        traded=sum(abs(live.get(k,0.0)-prev.get(k,0.0)) for k in set(live)|set(prev))
        linear_cost=traded*cost_bps/10000.0
        short_gross=sum(-v for v in live.values() if v<0)
        long_gross=sum(v for v in live.values() if v>0)
        carry_cost=(short_gross*borrow_bps + long_gross*financing_bps)/10000.0/252.0
        total_cost=linear_cost+carry_cost
        net=gross_ret-total_cost
        equity*=1+net
        returns.append(net); eq.append(equity); costs.append(total_cost); turnovers.append(traded/2)
        es=exposure_stats(live)
        names.append(es["names"]); gross_exps.append(es["gross"]); net_exps.append(es["net"]); hhis.append(es["hhi"]); max_weights.append(es["max_abs"])

        # Capacity diagnostic for changed positions only; does not alter research weights.
        day_parts=[]
        if capital>0:
            for k in set(live)|set(prev):
                dw=abs(live.get(k,0)-prev.get(k,0))
                row=yesterday.get(k) or today.get(k)
                if not row or dw<=0: continue
                px=number(row,"close"); adv=number(row,"adv20")
                if ok(px) and ok(adv) and px>0 and adv>0:
                    part=(dw*capital)/(px*adv)
                    day_parts.append(part)
                    if part>max_part: capacity_breaches+=1
        if day_parts: participation.extend(day_parts)

        rows_out.append({"pnl_date":pnl_day,"signal_date":signal_day,"gross_return":gross_ret,"traded_notional":traded,
                         "one_way_turnover":traded/2,"linear_cost":linear_cost,"carry_cost":carry_cost,"net_return":net,
                         "equity":equity,"names":es["names"],"gross_exposure":es["gross"],"net_exposure":es["net"],
                         "hhi":es["hhi"],"max_abs_weight":es["max_abs"]})
        prev=live

    if output_csv:
        output_csv=Path(output_csv); output_csv.parent.mkdir(parents=True,exist_ok=True)
        cols=list(rows_out[0]) if rows_out else ["pnl_date","signal_date"]
        with output_csv.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows_out)
    m=_metrics(returns,eq)
    active_idx=[i for i,r in enumerate(rows_out) if r["gross_exposure"]>1e-12]
    if active_idx:
        first_active=active_idx[0]
        active_returns=returns[first_active:]
        active_eq=[];ax=1.0
        for rr in active_returns:
            ax*=1+rr;active_eq.append(ax)
        active_metrics=_metrics(active_returns,active_eq)
        active_start=rows_out[first_active]["pnl_date"]
    else:
        active_metrics=_metrics([],[])
        active_start=None
    m.update({
        "days":len(returns),"active_days":len(active_returns) if active_idx else 0,"active_start_date":active_start,"active_period_metrics":active_metrics,
        "last_equity":equity,"avg_one_way_turnover":mean(turnovers) if turnovers else None,
        "total_cost_fraction":sum(costs),"avg_names":mean(names) if names else None,
        "avg_gross_exposure":mean(gross_exps) if gross_exps else None,"avg_net_exposure":mean(net_exps) if net_exps else None,
        "avg_hhi":mean(hhis) if hhis else None,"max_observed_abs_weight":max(max_weights) if max_weights else None,
        "cost_bps_per_dollar_traded":cost_bps,"delay_days":delay,"price_policy":price_policy,
        "return_source_counts":dict(return_source_counts),"capacity_capital":capital,"capacity_max_adv_participation":max_part,
        "capacity_breach_trade_count":capacity_breaches,"median_trade_adv_participation":median(participation) if participation else None,
        "max_trade_adv_participation":max(participation) if participation else None,
    })
    return rows_out,m


def yearly_metrics(backtest_rows):
    buckets=defaultdict(list)
    for r in backtest_rows:
        buckets[r["pnl_date"][:4]].append(r["net_return"])
    out={}
    for year,rs in sorted(buckets.items()):
        eq=[];x=1.0
        for r in rs: x*=1+r; eq.append(x)
        out[year]=_metrics(rs,eq)
    return out


def split_metrics(backtest_rows, os_start):
    if not os_start: return None
    out={}
    for label,predicate in (("IS",lambda d:d<os_start),("OS",lambda d:d>=os_start)):
        rs=[r["net_return"] for r in backtest_rows if predicate(r["pnl_date"])]
        eq=[];x=1.0
        for r in rs: x*=1+r;eq.append(x)
        out[label]=_metrics(rs,eq)
        out[label]["days"]=len(rs)
    return out


def ic_report(dates, signals, delay_days=1):
    days=sorted(dates); ics=[]
    offset=delay_days+1
    for i in range(offset,len(days)):
        sd=days[i-offset]; pd=days[i]; prev=days[i-1]
        rets={}
        for k in signals.get(sd,{}):
            if k in dates[pd] and k in dates[prev]:
                r,_=_realized_return(dates[pd][k],dates[prev][k])
                if ok(r): rets[k]=r
        ic=spearman(signals.get(sd,{}),rets)
        if ok(ic): ics.append(ic)
    if not ics:
        return {"days":0,"mean_spearman_ic":None,"ic_ir":None,"positive_ic_rate":None}
    sd=pstdev(ics) if len(ics)>1 else 0.0
    return {"days":len(ics),"mean_spearman_ic":mean(ics),"ic_ir":mean(ics)/sd*math.sqrt(252) if sd>0 else None,
            "positive_ic_rate":sum(x>0 for x in ics)/len(ics),"ic_std":sd}


def block_bootstrap(backtest_rows, samples=300, block=20, seed=1729):
    rs=[r["net_return"] for r in backtest_rows]
    if len(rs)<max(40,block): return {"samples":0}
    rng=random.Random(seed); sharpes=[]; totals=[]
    n=len(rs)
    for _ in range(samples):
        sim=[]
        while len(sim)<n:
            start=rng.randrange(0,max(1,n-block+1));sim.extend(rs[start:start+block])
        sim=sim[:n]; eq=[];x=1.0
        for r in sim:x*=1+r;eq.append(x)
        m=_metrics(sim,eq)
        if m["annualized_net_sharpe"] is not None:sharpes.append(m["annualized_net_sharpe"])
        totals.append(m["total_return"])
    def pct(x,p):
        y=sorted(x);idx=min(len(y)-1,max(0,int(round((len(y)-1)*p))));return y[idx]
    return {"samples":samples,"block_days":block,"sharpe_p05":pct(sharpes,.05) if sharpes else None,
            "sharpe_p50":pct(sharpes,.50) if sharpes else None,"sharpe_p95":pct(sharpes,.95) if sharpes else None,
            "total_return_p05":pct(totals,.05),"total_return_p50":pct(totals,.50),"total_return_p95":pct(totals,.95)}


def cost_stress(dates,signals,cfg,levels=(0,5,10,20,50)):
    out={}
    for bps in levels:
        _,m=run_strategy(dates,signals,cfg,cost_bps=bps,price_policy="error")
        out[str(bps)]={k:m.get(k) for k in ("annualized_net_sharpe","cagr","total_return","max_drawdown","total_cost_fraction")}
    return out
