import json,tempfile,unittest
from pathlib import Path
from make_sample import make_sample
from data_layer import load_panel
from signal_engine import compute
from backtest import run_strategy,ic_report
from ibkr_paper import delta_orders,preflight_or_raise
class TestBacktestIBKR(unittest.TestCase):
    def setUp(self):self.cfg=json.loads((Path(__file__).parents[1]/"config.json").read_text())
    def test_smoke_backtest(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.csv";make_sample(p,names=80,days=240);d,q=load_panel(p);s,c,diag=compute(d,self.cfg)
            rows,m=run_strategy(d,s,self.cfg,cost_bps=10);self.assertGreater(len(rows),100);self.assertIn("annualized_net_sharpe",m);self.assertIn("mean_spearman_ic",ic_report(d,s))
    def test_delta_orders_not_full_targets(self):
        o,g=delta_orders({"A":.10},10000,{"A":100},{"A":6},5000,5000,25,10)
        self.assertEqual(o[0]["target_qty"],10);self.assertEqual(o[0]["delta_qty"],4);self.assertEqual(o[0]["status"],"READY")
    def test_order_limit(self):
        o,g=delta_orders({"A":.5},10000,{"A":100},{"A":0},5000,1000,25,10)
        self.assertEqual(o[0]["status"],"ORDER_LIMIT_BREACH")
        with self.assertRaises(RuntimeError):preflight_or_raise(o,g,100000)
    def test_removed_managed_symbol_closes(self):
        o,g=delta_orders({"A":.10},10000,{"A":100,"B":50},{"A":10,"B":4},5000,5000,25,10,managed_symbols={"A","B"})
        b=next(x for x in o if x["ticker"]=="B")
        self.assertEqual(b["target_qty"],0);self.assertEqual(b["delta_qty"],-4);self.assertEqual(b["status"],"READY")
if __name__=="__main__":unittest.main()
