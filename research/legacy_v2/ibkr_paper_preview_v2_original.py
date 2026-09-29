"""IBKR PAPER preview helper for Estimate-Link v2.0.

This module intentionally does not place orders. It converts the latest target weights
into a paper-trading order preview after reading account value and market prices from IBKR.
Requires: pip install ib_async
"""
import argparse
import csv
import json
from pathlib import Path

PAPER_PORTS = {7497, 4002}


def latest_targets(path: Path):
    rows = list(csv.DictReader(path.open(encoding='utf-8-sig')))
    if not rows:
        raise ValueError('signals.csv is empty')
    latest = max(r['date'] for r in rows)
    vals = {r['ticker']: float(r['target_weight']) for r in rows if r['date'] == latest and r['target_weight']}
    return latest, vals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--signals', type=Path, required=True)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=7497)
    ap.add_argument('--client-id', type=int, default=1810)
    ap.add_argument('--capital', type=float, default=0, help='0 = use NetLiquidation from paper account')
    ap.add_argument('--max-name-notional', type=float, default=5000)
    ap.add_argument('--output', type=Path, default=Path('paper_order_preview.json'))
    a = ap.parse_args()
    if a.port not in PAPER_PORTS:
        raise SystemExit(f'Refusing non-paper IBKR port {a.port}. Allowed: {sorted(PAPER_PORTS)}')
    try:
        from ib_async import IB, Stock
    except ImportError:
        raise SystemExit('Install ib_async first: pip install ib_async')

    date, targets = latest_targets(a.signals)
    ib = IB(); ib.connect(a.host, a.port, clientId=a.client_id, readonly=True, timeout=10)
    try:
        capital = a.capital
        if capital <= 0:
            vals = {x.tag: x.value for x in ib.accountSummary()}
            capital = float(vals.get('NetLiquidation', 0))
        if capital <= 0:
            raise RuntimeError('Could not determine positive paper-account capital')
        preview=[]
        for ticker, weight in sorted(targets.items()):
            c=Stock(ticker,'SMART','USD'); ib.qualifyContracts(c)
            t=ib.reqMktData(c,'',False,False); ib.sleep(1.0)
            px=t.marketPrice()
            if px is None or px != px or px <= 0:
                preview.append({'ticker':ticker,'weight':weight,'status':'NO_PRICE'}); continue
            notional=max(-a.max_name_notional,min(a.max_name_notional,weight*capital))
            qty=int(abs(notional)/px)
            side='BUY' if notional>0 else 'SELL'
            preview.append({'ticker':ticker,'weight':weight,'price':px,'notional':notional,
                            'side':side,'quantity':qty,'status':'PREVIEW_ONLY'})
        payload={'signal_date':date,'capital':capital,'paper_port':a.port,
                 'readonly':True,'orders':preview,
                 'warning':'Preview only. This script contains no placeOrder call.'}
        a.output.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        print(json.dumps(payload,indent=2))
    finally:
        ib.disconnect()

if __name__=='__main__':
    main()
