"""Estimate-Link × Certainty × IV180 Sector Hybrid v2.0.

Offline research engine approximating WorldQuant BRAIN alpha levWKewl.
No live orders. Point-in-time licensed input data is required for meaningful results.
"""
import argparse
import csv
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from statistics import mean, pstdev

FIELDS = ('date ticker sector industry open high low close volume est_ptp est_fcf est_eps '
          'earnings_certainty_rank_derivative implied_volatility_call_180 '
          'implied_volatility_put_180').split()
NAN = float('nan')


def ok(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def number(row, key):
    try:
        value = row.get(key, '')
        return float(value) if str(value).strip() else NAN
    except (TypeError, ValueError):
        return NAN


def full(hist, n):
    x = list(hist)[-n:]
    return x if len(x) == n and all(map(ok, x)) else None


def backfill(hist, n):
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
    # BRAIN approximation: midpoint percentile for ties.
    x = full(hist, n)
    return (sum(v < x[-1] for v in x) + .5*sum(v == x[-1] for v in x))/n if x else NAN


def rank(vals):
    # BRAIN approximation: centered percentile ranks in (0,1).
    ordered = sorted((v, k) for k, v in vals.items() if ok(v))
    result = {k: NAN for k in vals}
    i = 0
    while i < len(ordered):
        j = i+1
        while j < len(ordered) and ordered[j][0] == ordered[i][0]:
            j += 1
        for _, k in ordered[i:j]:
            result[k] = (i+j)/(2*len(ordered))
        i = j
    return result


def group(vals, labels, mode):
    buckets = defaultdict(dict)
    for k, v in vals.items():
        buckets[labels.get(k, '')][k] = v
    result = {}
    for entries in buckets.values():
        if mode == 'rank':
            result.update(rank(entries))
            continue
        good = [v for v in entries.values() if ok(v)]
        center = mean(good) if good else NAN
        sd = pstdev(good) if len(good) > 1 else 0
        for k, v in entries.items():
            if not ok(v):
                result[k] = NAN
            elif mode == 'neutral':
                result[k] = v-center
            else:
                result[k] = (v-center)/sd if sd else 0.0
    return result


def trade_when_step(entry, alpha, exit_cond, previous=NAN):
    """Approximate BRAIN trade_when state transition."""
    if ok(exit_cond) and exit_cond > 0:
        return NAN
    if entry:
        return alpha if ok(alpha) else previous
    return previous


def load(path):
    dates = defaultdict(dict)
    with open(path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        missing = set(FIELDS)-set(reader.fieldnames or [])
        if missing:
            raise ValueError('Missing CSV columns: ' + ', '.join(sorted(missing)))
        for row in reader:
            date, ticker = row['date'].strip(), row['ticker'].strip()
            if not date or not ticker:
                raise ValueError('Blank date or ticker')
            if ticker in dates[date]:
                raise ValueError('Duplicate date/ticker: ' + date + ' ' + ticker)
            dates[date][ticker] = row
    return dates


def compute(dates, adv20_mode='auto', include_components=False):
    history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=240)))
    held = {}
    signals = {}
    components = {}
    for date, rows in sorted(dates.items()):
        sectors = {k: r['sector'] for k, r in rows.items()}
        industries = {k: r['industry'] for k, r in rows.items()}
        stable, certainty, iv180, ranges, volumes, adv20 = {}, {}, {}, {}, {}, {}
        for k, r in rows.items():
            h = history[k]
            for field in ('est_ptp', 'est_fcf', 'est_eps'):
                h[field].append(number(r, field))
                h[field+'_bf'].append(backfill(h[field], 150))
            p, f, e = [h[field+'_bf'] for field in ('est_ptp', 'est_fcf', 'est_eps')]
            cs = [corr(p, f, 22), corr(p, e, 22), corr(f, e, 22)]
            h['stable'].append(-sum(w*v for w, v in zip((.4,.3,.3), cs)) if all(map(ok, cs)) else NAN)
            stable[k] = decay(h['stable'], 7)

            h['certainty'].append(number(r, 'earnings_certainty_rank_derivative'))
            certainty[k] = tsrank(h['certainty'], 84)

            call = number(r, 'implied_volatility_call_180')
            put = number(r, 'implied_volatility_put_180')
            h['ivraw'].append(call-put if ok(call) and ok(put) else NAN)
            h['ivbf'].append(backfill(h['ivraw'], 55))
            iv = full(h['ivbf'], 32)
            iv180[k] = mean(iv) if iv else NAN

            o, hi, lo, cl = [number(r, field) for field in ('open','high','low','close')]
            h['range'].append((cl-o)/(hi-lo) if all(map(ok, (o,hi,lo,cl))) and hi > lo else NAN)
            ranges[k] = decay(h['range'], 5)

            volumes[k] = number(r, 'volume')
            h['volume'].append(volumes[k])
            supplied_adv = number(r, 'adv20')
            volwindow = full(h['volume'], 20)
            rolling_adv = mean(volwindow) if volwindow else NAN
            if adv20_mode == 'input':
                adv20[k] = supplied_adv
            elif adv20_mode == 'rolling':
                adv20[k] = rolling_adv
            else:
                adv20[k] = supplied_adv if ok(supplied_adv) else rolling_adv

        link = group(stable, sectors, 'rank')
        cert = group(certainty, sectors, 'rank')
        ivz = group(iv180, sectors, 'zscore')
        mixed = {k: .6*link[k]+.2*cert[k]+.2*ivz[k]
                 if all(map(ok, (link[k],cert[k],ivz[k]))) else NAN for k in rows}
        core = group(mixed, sectors, 'neutral')
        range_rank = rank(ranges)
        trade = {}
        for k in rows:
            entry = ok(volumes[k]) and ok(adv20[k]) and volumes[k] > .85*adv20[k]
            alpha = -range_rank[k] if ok(range_rank[k]) else NAN
            held[k] = trade_when_step(entry, alpha, 0.0, held.get(k, NAN))
            trade[k] = held[k]
        rng = group(trade, industries, 'neutral')

        result = {}
        day_components = {}
        for k in rows:
            h = history[k]
            h['core'].append(core[k])
            core4 = decay(h['core'], 4)
            raw = .65*core4+.35*rng[k] if ok(core4) and ok(rng[k]) else NAN
            h['final'].append(raw)
            final5 = decay(h['final'], 5)  # platform decay=5 approximation
            result[k] = final5
            if include_components:
                day_components[k] = {
                    'stable': stable[k], 'link_alpha': link[k], 'certainty': cert[k],
                    'iv180': ivz[k], 'core': core[k], 'core_decay4': core4,
                    'range_decay5': ranges[k], 'rng': rng[k], 'pre_platform_decay': raw,
                    'final_signal': final5, 'adv20_used': adv20[k],
                }
        signals[date] = result
        if include_components:
            components[date] = day_components
    return (signals, components) if include_components else signals


def weights(signal, cap=.06, gross_target=1.0, tol=1e-12):
    """Approximate market-neutral capped portfolio with iterative redistribution.

    Unlike v1, this explicitly restores gross exposure after capping where feasible.
    """
    values = {k:v for k,v in signal.items() if ok(v)}
    if len(values) < 2:
        return {}
    m = mean(values.values())
    centered = {k:v-m for k,v in values.items()}
    gross = sum(map(abs, centered.values()))
    if gross <= tol:
        return {}
    w = {k:v/gross*gross_target for k,v in centered.items()}

    # Alternating projection: cap -> dollar-neutral -> gross target.
    for _ in range(100):
        w = {k:max(-cap, min(cap, v)) for k,v in w.items()}
        free = [k for k,v in w.items() if abs(v) < cap-1e-10]
        net = sum(w.values())
        if free and abs(net) > tol:
            adj = net/len(free)
            for k in free:
                w[k] -= adj
        gross = sum(abs(v) for v in w.values())
        if gross > tol:
            free = [k for k,v in w.items() if abs(v) < cap-1e-10]
            if free:
                fixed_gross = sum(abs(v) for k,v in w.items() if k not in free)
                free_gross = sum(abs(w[k]) for k in free)
                desired_free = max(0.0, gross_target-fixed_gross)
                if free_gross > tol:
                    scale = desired_free/free_gross
                    for k in free:
                        w[k] *= scale
        if abs(sum(w.values())) < 1e-10 and abs(sum(abs(v) for v in w.values())-gross_target) < 1e-8 and all(abs(v) <= cap+1e-10 for v in w.values()):
            break
    w = {k:max(-cap, min(cap, v)) for k,v in w.items()}
    return w


def _annual_metrics(returns, equity_curve):
    if not returns:
        return {'annualized_return_arithmetic': None, 'annualized_volatility': None,
                'annualized_net_sharpe': None, 'cagr': None, 'hit_rate': None}
    ann_ret = mean(returns)*252
    vol_d = pstdev(returns) if len(returns) > 1 else 0.0
    ann_vol = vol_d*math.sqrt(252)
    sharpe = mean(returns)/vol_d*math.sqrt(252) if vol_d > 0 else None
    years = len(returns)/252
    cagr = equity_curve[-1]**(1/years)-1 if years > 0 and equity_curve[-1] > 0 else None
    hit = sum(r > 0 for r in returns)/len(returns)
    return {'annualized_return_arithmetic': ann_ret, 'annualized_volatility': ann_vol,
            'annualized_net_sharpe': sharpe, 'cagr': cagr, 'hit_rate': hit}


def run(source, output, cost_bps, min_names, adv20_mode='auto', missing_held_policy='error',
        cost_convention='traded_notional'):
    dates = load(source)
    signals, components = compute(dates, adv20_mode=adv20_mode, include_components=True)
    days = sorted(dates)
    output.mkdir(parents=True, exist_ok=True)
    targets = {d:weights(signals[d]) for d in days}

    with open(output/'signals.csv','w',newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['date','ticker','raw_signal','target_weight'])
        for d in days:
            for k,v in sorted(signals[d].items()):
                if ok(v):
                    writer.writerow([d,k,v,targets[d].get(k,0)])

    with open(output/'components.csv','w',newline='') as file:
        cols = ['date','ticker','stable','link_alpha','certainty','iv180','core','core_decay4',
                'range_decay5','rng','pre_platform_decay','final_signal','adv20_used']
        writer = csv.writer(file); writer.writerow(cols)
        for d in days:
            for k,c in sorted(components[d].items()):
                writer.writerow([d,k] + [c.get(x, NAN) for x in cols[2:]])

    equity, peak, max_dd, prev, returns, equity_curve = 1.,1.,0.,{},[],[]
    total_cost = 0.0
    turnovers = []
    traded_notionals = []
    name_counts = []
    gross_exposures = []
    net_exposures = []

    with open(output/'backtest.csv','w',newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['pnl_date','signal_date','gross_return','one_way_turnover','traded_notional',
                         'cost','net_return','equity','names','gross_exposure','net_exposure'])
        for i in range(2,len(days)):
            target = targets[days[i-2]]
            if len(target) < min_names:
                target = {}
            today, yesterday = dates[days[i]], dates[days[i-1]]

            held_missing = [k for k,v in target.items() if abs(v) > 0 and (k not in today or k not in yesterday)]
            if held_missing and missing_held_policy == 'error':
                raise ValueError(
                    f'Held names missing price rows on {days[i]}: {held_missing[:8]}. '
                    'Provide explicit delisting/exit data or use --missing-held-policy drop for plumbing only.'
                )

            live = {k:v for k,v in target.items() if k in today and k in yesterday
                    and ok(number(today[k],'close')) and ok(number(yesterday[k],'close'))
                    and number(yesterday[k],'close') > 0}
            gross = sum(v*(number(today[k],'close')/number(yesterday[k],'close')-1) for k,v in live.items())

            traded = sum(abs(live.get(k,0)-prev.get(k,0)) for k in set(live)|set(prev))
            one_way_turnover = traded/2
            if cost_convention == 'half_turnover':
                cost_base = one_way_turnover
            else:
                cost_base = traded
            cost = cost_base*cost_bps/10000
            net = gross-cost
            equity *= 1+net
            peak = max(peak,equity)
            max_dd = max(max_dd,1-equity/peak)
            returns.append(net); equity_curve.append(equity)
            total_cost += cost
            turnovers.append(one_way_turnover); traded_notionals.append(traded)
            name_counts.append(len(live))
            gross_exp = sum(abs(v) for v in live.values()); net_exp = sum(live.values())
            gross_exposures.append(gross_exp); net_exposures.append(net_exp)
            writer.writerow([days[i],days[i-2],gross,one_way_turnover,traded,cost,net,equity,len(live),gross_exp,net_exp])
            prev = live

    metrics = _annual_metrics(returns, equity_curve)
    report = {
        'engine_version':'2.0', 'alpha_id':'levWKewl','days':len(returns),'last_equity':equity,
        **metrics, 'max_drawdown':max_dd, 'total_return':equity-1, 'total_cost_fraction':total_cost,
        'avg_one_way_turnover': mean(turnovers) if turnovers else None,
        'avg_traded_notional': mean(traded_notionals) if traded_notionals else None,
        'avg_names': mean(name_counts) if name_counts else None,
        'avg_gross_exposure': mean(gross_exposures) if gross_exposures else None,
        'avg_net_exposure': mean(net_exposures) if net_exposures else None,
        'cost_bps':cost_bps, 'cost_convention':cost_convention, 'min_names':min_names,
        'adv20_mode':adv20_mode, 'missing_held_policy':missing_held_policy,
        'warning':'Offline BRAIN approximation only. Synthetic sample results are not financial evidence. No live orders.'
    }
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=Path('output'))
    parser.add_argument('--cost-bps',type=float,default=10,
                        help='Cost in bps per dollar traded when --cost-convention=traded_notional.')
    parser.add_argument('--cost-convention',choices=('traded_notional','half_turnover'),default='traded_notional')
    parser.add_argument('--min-names',type=int,default=20)
    parser.add_argument('--adv20-mode',choices=('auto','input','rolling'),default='auto',
                        help='auto prefers an optional CSV adv20 column; otherwise computes rolling 20d share volume.')
    parser.add_argument('--missing-held-policy',choices=('error','drop'),default='error',
                        help='error prevents silent delisting/missing-return bias; drop is for plumbing checks only.')
    args = parser.parse_args()
    if args.cost_bps < 0 or args.min_names < 1:
        parser.error('cost-bps must be >=0 and min-names must be >=1')
    run(args.input,args.output,args.cost_bps,args.min_names,args.adv20_mode,
        args.missing_held_policy,args.cost_convention)
