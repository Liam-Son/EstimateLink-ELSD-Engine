"""IBKR paper-trading adapter: delta-aware preview by default, guarded paper execution optional.

Default mode is read-only preview. Execution requires ALL of:
  --execute-paper --ack PAPER_ONLY --account <paper account>
and a configured paper port (7497 or 4002 by default).

A persistent state file tracks ONLY symbols managed by this strategy. This lets the
adapter close prior strategy positions that disappear from the latest target while
avoiding unrelated holdings in the same paper account.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,json,math
from pathlib import Path

PAPER_PORTS={7497,4002}
ORDER_REF="EstimateLink_v3_PAPER"

def latest_targets(path):
    rows=list(csv.DictReader(Path(path).open(encoding="utf-8-sig")))
    if not rows:raise ValueError("signals.csv is empty")
    latest=max(r["date"] for r in rows)
    vals={r["ticker"]:float(r["target_weight"]) for r in rows if r["date"]==latest and r.get("target_weight","").strip()}
    return latest,vals

def validate_signal_age(date,max_age):
    d=dt.date.fromisoformat(date);age=(dt.date.today()-d).days
    if age<0:raise ValueError("Signal date is in the future")
    if age>max_age:raise ValueError(f"Signal is stale: {age} calendar days old > {max_age}")
    return age

def load_state(path):
    path=Path(path)
    if not path.exists():return {"managed_symbols":[],"last_signal_date":None}
    x=json.loads(path.read_text(encoding="utf-8"))
    return {"managed_symbols":sorted(set(x.get("managed_symbols",[]))),"last_signal_date":x.get("last_signal_date")}

def save_state(path,managed_symbols,signal_date):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"managed_symbols":sorted(set(managed_symbols)),"last_signal_date":signal_date},indent=2),encoding="utf-8")

def delta_orders(targets,capital,prices,current_positions,max_name,max_order,min_order,max_orders,managed_symbols=None):
    managed=set(managed_symbols or [])|set(targets)
    orders=[];gross=0.0
    for ticker in sorted(managed):
        weight=float(targets.get(ticker,0.0))
        px=prices.get(ticker)
        current_qty=int(round(current_positions.get(ticker,0)))
        if px is None or not math.isfinite(px) or px<=0:
            # A quote is only required when a position exists or target is nonzero.
            status="NO_PRICE" if current_qty!=0 or abs(weight)>0 else "NO_ACTION"
            orders.append({"ticker":ticker,"weight":weight,"current_qty":current_qty,"status":status});continue
        target_notional=max(-max_name,min(max_name,weight*capital))
        target_qty=int(abs(target_notional)/px)*(1 if target_notional>=0 else -1)
        delta=target_qty-current_qty
        delta_notional=delta*px
        gross+=abs(target_qty*px)
        if abs(delta_notional)<min_order:
            status="NO_ACTION"
        elif abs(delta_notional)>max_order:
            status="ORDER_LIMIT_BREACH"
        else:
            status="READY"
        orders.append({"ticker":ticker,"weight":weight,"price":px,"current_qty":current_qty,"target_qty":target_qty,
                       "delta_qty":delta,"delta_notional":delta_notional,"side":"BUY" if delta>0 else "SELL" if delta<0 else "NONE",
                       "status":status,"borrow_check_required":target_qty<0})
    ready=[o for o in orders if o.get("status")=="READY"]
    if len(ready)>max_orders:
        raise ValueError(f"Ready order count {len(ready)} exceeds max_orders {max_orders}")
    return orders,gross

def preflight_or_raise(orders,gross,max_gross):
    if gross>max_gross:raise RuntimeError(f"Target gross notional {gross:.2f} exceeds limit {max_gross:.2f}")
    blockers=[o for o in orders if o.get("status") in {"NO_PRICE","ORDER_LIMIT_BREACH"}]
    if blockers:raise RuntimeError(f"Preflight blocked; resolve all quote/order-limit failures before execution: {blockers[:8]}")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signals",type=Path,required=True);ap.add_argument("--host",default="127.0.0.1");ap.add_argument("--port",type=int,default=7497)
    ap.add_argument("--client-id",type=int,default=1810);ap.add_argument("--account",default=None);ap.add_argument("--capital",type=float,default=0)
    ap.add_argument("--max-gross-notional",type=float,default=100000);ap.add_argument("--max-name-notional",type=float,default=5000)
    ap.add_argument("--max-order-notional",type=float,default=5000);ap.add_argument("--min-order-notional",type=float,default=25)
    ap.add_argument("--max-orders",type=int,default=100);ap.add_argument("--max-signal-age-days",type=int,default=4)
    ap.add_argument("--state",type=Path,default=Path("estimate_link_paper_state.json"));ap.add_argument("--output",type=Path,default=Path("paper_order_plan.json"))
    ap.add_argument("--execute-paper",action="store_true");ap.add_argument("--ack",default="",help="Execution requires exact text PAPER_ONLY")
    a=ap.parse_args()
    if a.port not in PAPER_PORTS:raise SystemExit(f"Refusing non-paper port {a.port}. Allowed: {sorted(PAPER_PORTS)}")
    if a.execute_paper and (a.ack!="PAPER_ONLY" or not a.account):raise SystemExit("Paper execution requires --ack PAPER_ONLY and explicit --account")
    try:from ib_async import IB,Stock,MarketOrder
    except ImportError:raise SystemExit("Install ib_async first: pip install -r requirements.txt")
    date,targets=latest_targets(a.signals);age=validate_signal_age(date,a.max_signal_age_days);state=load_state(a.state)
    managed=set(state["managed_symbols"])|set(targets)
    ib=IB();ib.connect(a.host,a.port,clientId=a.client_id,readonly=not a.execute_paper,timeout=10,account=a.account or "")
    try:
        accounts=ib.managedAccounts();account=a.account or (accounts[0] if len(accounts)==1 else None)
        if not account:raise RuntimeError(f"Specify --account; connected accounts: {accounts}")
        if account not in accounts:raise RuntimeError(f"Account {account} is not available on this session")
        capital=a.capital
        if capital<=0:
            vals={x.tag:x.value for x in ib.accountSummary(account)};capital=float(vals.get("NetLiquidation",0))
        if capital<=0:raise RuntimeError("Could not determine positive account capital")
        pos={p.contract.symbol:p.position for p in ib.positions(account)}
        contracts={};prices={}
        for ticker in managed:
            c=Stock(ticker,"SMART","USD");qualified=ib.qualifyContracts(c)
            if qualified:contracts[ticker]=c
        if contracts:
            # One snapshot call in a fresh session; avoids repeated snapshot reuse in this adapter.
            ticks=ib.reqTickers(*contracts.values())
            for t in ticks:
                px=t.marketPrice()
                if px is not None and math.isfinite(px) and px>0:prices[t.contract.symbol]=float(px)
        orders,gross=delta_orders(targets,capital,prices,pos,a.max_name_notional,a.max_order_notional,a.min_order_notional,a.max_orders,managed)
        payload={"signal_date":date,"signal_age_days":age,"account":account,"capital":capital,"paper_port":a.port,"readonly":not a.execute_paper,
                 "target_gross_notional":gross,"managed_symbols_before":sorted(state["managed_symbols"]),"orders":orders,"executed":False,
                 "warning":"Paper-port guard only. Confirm TWS/Gateway session itself is a paper account before execution."}
        if a.execute_paper:
            # Fail closed: no partial rebalance if any required quote/risk check failed.
            preflight_or_raise(orders,gross,a.max_gross_notional)
            existing=[t for t in ib.openTrades() if getattr(t.order,"orderRef","")==ORDER_REF]
            if existing:raise RuntimeError(f"Existing open {ORDER_REF} orders detected; resolve them before a new rebalance")
            submitted=[]
            for o in orders:
                if o.get("status")!="READY" or o["delta_qty"]==0:continue
                order=MarketOrder(o["side"],abs(o["delta_qty"]),account=account,orderRef=ORDER_REF,tif="DAY",outsideRth=False)
                trade=ib.placeOrder(contracts[o["ticker"]],order)
                submitted.append({"ticker":o["ticker"],"orderId":trade.order.orderId,"side":o["side"],"qty":abs(o["delta_qty"])})
            ib.sleep(1.0);payload["executed"]=True;payload["submitted"]=submitted
            save_state(a.state,targets.keys(),date)
        else:
            # Preview never changes live strategy state. It can be reviewed safely and repeatedly.
            payload["state_update_if_executed"]={"managed_symbols":sorted(targets),"last_signal_date":date}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2),encoding="utf-8");print(json.dumps(payload,indent=2))
    finally:ib.disconnect()
if __name__=="__main__":main()
