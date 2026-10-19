"""Tests for NGFS conversion, annual interpolation and Fisher (plan 02-12)."""
import unittest

from checkmodel.baseline_reference import model_values
from checkmodel.carbon_reference import (carbon_paths, eua_gaps,
                                         eur_route_factor, interp_annual,
                                         usd_to_eur2025)
from checkmodel.rates_reference import discount_rate_real, fisher_real
from config.build_config import BUILD
from config.inputs import INPUTS

V = model_values(INPUTS)
BY_ID = {r.id: r for r in INPUTS}
REL = 1e-12


class ConversionTests(unittest.TestCase):
    def test_factor(self):
        f = eur_route_factor(V, 2010)
        self.assertAlmostEqual(f / ((128.75 / 93.14) / 1.3257), 1.0, delta=REL)
        self.assertAlmostEqual(f / 1.0427153041888453, 1.0, delta=REL)

    def test_usd_to_eur(self):
        f = eur_route_factor(V, 2010)
        for x, e in ((216.911391375443, 226.17682744007072),
                     (898.2429363719594, 936.6116566345693)):
            self.assertAlmostEqual(usd_to_eur2025(x, f) / e, 1.0, delta=REL)

    def test_missing_input(self):
        with self.assertRaises(ValueError) as c:
            eur_route_factor(V, 2011)
        self.assertIn("2011", str(c.exception))
        v = dict(V)
        del v["Fin_HICP_EA_2010"]
        with self.assertRaises(ValueError):
            eur_route_factor(v, 2010)


class InterpTests(unittest.TestCase):
    def test_flat_after_last(self):
        out = interp_annual([2025, 2030, 2035], [10.0, 20.0, 40.0],
                            range(2026, 2041))
        self.assertEqual(out, [12, 14, 16, 18, 20, 24, 28, 32, 36, 40,
                               40, 40, 40, 40, 40])

    def test_anchor_hits(self):
        out = interp_annual([2025, 2030, 2035], [10.0, 20.0, 40.0],
                            range(2026, 2036))
        self.assertEqual(out[4], 20.0)
        self.assertEqual(out[9], 40.0)

    def test_bad_input(self):
        for ya in ([2025], [2030, 2025, 2035], [2026, 2030]):
            with self.assertRaises(ValueError):
                interp_annual(ya, [1.0] * len(ya), range(2026, 2030))


class PathTests(unittest.TestCase):
    def test_paths(self):
        p = carbon_paths(INPUTS)
        self.assertEqual(sorted(p), ["CP", "NDC", "NZ50"])
        f = eur_route_factor(V, 2010)
        anchors = {"CP": 24.27635219154393, "NDC": 126.75982143607783,
                   "NZ50": 158.89362281553187}
        for k, (ay, av, annual) in p.items():
            self.assertEqual(len(annual), 30)
            self.assertAlmostEqual(av[0] / anchors[k], 1.0, delta=REL)
            r = BY_ID["Carbon_NGFS_" + k]
            for y, pub in r.series:
                got = annual[y - BUILD.timeline_start]
                self.assertAlmostEqual(got / (pub * f), 1.0, delta=REL)

    def test_gaps(self):
        g = eua_gaps(INPUTS)
        self.assertAlmostEqual(g["CP"], 73.43 - 24.27635219154393, places=9)
        self.assertAlmostEqual(g["NDC"], 73.43 - 126.75982143607783, places=9)
        self.assertAlmostEqual(g["NZ50"], 73.43 - 158.89362281553187,
                               places=9)


class FisherTests(unittest.TestCase):
    def test_fisher(self):
        self.assertAlmostEqual(fisher_real(0.07811, 0.02) / (1.07811 / 1.02 - 1),
                               1.0, delta=REL)
        self.assertAlmostEqual(fisher_real(0.07811, 0.02),
                               0.05697058823529411, delta=1e-15)

    def test_discount(self):
        self.assertAlmostEqual(discount_rate_real(V),
                               fisher_real(0.07811, 0.02), delta=1e-15)


class ImportTests(unittest.TestCase):
    def test_stdlib_only(self):
        import checkmodel.carbon_reference as m
        with open(m.__file__) as fh:
            src = fh.read()
        for line in src.splitlines():
            if line.startswith(("import ", "from ")):
                self.assertRegex(line, r"^(from|import) (typing|config|checkmodel)")


if __name__ == "__main__":
    unittest.main()
