import math,unittest
from operators import backfill,corr,decay,tsrank,rank,group,trade_when_step,spearman
class TestOperators(unittest.TestCase):
    def test_backfill_window(self):
        self.assertEqual(backfill([1,float("nan"),3,float("nan")],2),3)
        self.assertTrue(math.isnan(backfill([1,float("nan"),float("nan")],2)))
    def test_corr_decay_rank(self):
        self.assertAlmostEqual(corr([1,2,3],[2,4,6],3),1.0)
        self.assertAlmostEqual(decay([1,2,3],3),14/6)
        self.assertAlmostEqual(tsrank([1,2,3],3),2.5/3)
        self.assertAlmostEqual(rank({"a":1,"b":3,"c":2})["b"],2.5/3)
    def test_group(self):
        x=group({"a":1,"b":3},{"a":"X","b":"X"},"neutral")
        self.assertAlmostEqual(sum(x.values()),0.0)
    def test_trade_when(self):
        p=float("nan");p=trade_when_step(True,.25,0,p);self.assertEqual(p,.25);p=trade_when_step(False,-.9,0,p);self.assertEqual(p,.25);p=trade_when_step(False,.1,1,p);self.assertTrue(math.isnan(p))
    def test_spearman(self):
        self.assertAlmostEqual(spearman({"a":1,"b":2,"c":3},{"a":4,"b":5,"c":6}),1.0)
if __name__=="__main__":unittest.main()
