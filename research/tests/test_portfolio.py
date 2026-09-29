import random,unittest
from portfolio import weights
class TestPortfolio(unittest.TestCase):
    def test_neutral_cap_gross(self):
        sig={f"T{i}":i for i in range(50)};w=weights(sig,.06,1.0)
        self.assertLess(abs(sum(w.values())),1e-10);self.assertLessEqual(max(map(abs,w.values())),.060000001);self.assertAlmostEqual(sum(map(abs,w.values())),1.0,places=10)
    def test_infeasible_stays_neutral(self):
        w=weights({"a":1,"b":2,"c":3},.01,1.0)
        self.assertLess(abs(sum(w.values())),1e-10);self.assertLessEqual(sum(map(abs,w.values())),1.0);self.assertLessEqual(max(map(abs,w.values())),.010000001)
    def test_fuzz_constraints(self):
        for n in range(3,80):
            random.seed(n);sig={f"T{i}":random.gauss(0,1) for i in range(n)};w=weights(sig,.06,1.0)
            if w:
                self.assertLess(abs(sum(w.values())),1e-9);self.assertLessEqual(max(map(abs,w.values())),.060000001);self.assertLessEqual(sum(map(abs,w.values())),1.000000001)
if __name__=="__main__":unittest.main()
