import tempfile,unittest,json
from pathlib import Path
from make_sample import make_sample
from data_layer import load_panel
from signal_engine import compute
from operators import ok
class TestDataSignal(unittest.TestCase):
    def setUp(self):self.cfg=json.loads((Path(__file__).parents[1]/"config.json").read_text())
    def test_gap_reset_differs_from_compress(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.csv";make_sample(p,names=30,days=220,with_gaps=True);d,q=load_panel(p)
            _,_,a=compute(d,self.cfg,gap_policy="reset");_,_,b=compute(d,self.cfg,gap_policy="compress")
            self.assertGreater(a["gap_resets"],0);self.assertEqual(b["gap_resets"],0)
    def test_strict_invalid_ohlc(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.csv";p.write_text("date,ticker,sector,industry,open,high,low,close,volume,est_ptp,est_fcf,est_eps,earnings_certainty_rank_derivative,implied_volatility_call_180,implied_volatility_put_180\n2024-01-02,A,S,I,10,9,8,10,100,1,1,1,1,.2,.2\n")
            with self.assertRaises(ValueError):load_panel(p,strict=True)
    def test_low_volume_exit_only_changes_held_range_after_volume_collapse(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"s.csv";make_sample(p,names=30,days=220)
            dates,_=load_panel(p)
            last=max(dates)
            for row in dates[last].values():
                row["volume"]="0"
            variant=json.loads((Path(__file__).parents[1]/"config_low_volume_exit.json").read_text(encoding="utf-8"))
            base_signals,base_components,_=compute(dates,self.cfg)
            variant_signals,variant_components,_=compute(dates,variant)
            self.assertTrue(any(ok(c["rng"]) for c in base_components[last].values()))
            self.assertTrue(all(not ok(c["rng"]) for c in variant_components[last].values()))
            for day in sorted(dates)[:-1]:
                for ticker in dates[day]:
                    a,b=base_signals[day][ticker],variant_signals[day][ticker]
                    self.assertTrue((not ok(a) and not ok(b)) or a==b)
if __name__=="__main__":unittest.main()
