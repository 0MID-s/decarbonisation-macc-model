import re
import unittest

from config import (inputs_baseline, inputs_carbon, inputs_constants,
                    inputs_factors, inputs_finance, inputs_measures,
                    inputs_prices)
from config._helpers import scalar, series, NA
from config.inputs import INPUTS
from config.schema import Kind, Status
from config.sources import SOURCES

MODS = (inputs_constants, inputs_baseline, inputs_prices, inputs_factors,
        inputs_carbon, inputs_finance, inputs_measures)
EXPECTED = {
    "Const_TJ_to_MWh": 1000 / 3.6, "Const_GJ_per_MWh": 3.6,
    "Const_kWh_per_MWh": 1000, "Const_g_per_kWh_to_t_per_MWh": 0.001,
    "Const_PctToFrac": 0.01, "Const_HoursPerYear": 8760,
    "Const_kg_per_t": 1000, "Const_g_per_kg": 1000,
    "Const_Mega_per_kilo": 1000, "Const_PerMW_to_PerkW": 0.001,
    "Const_CheckTolerance": 1e-6, "Const_km_per_100km": 100,
}
MONEY = re.compile(r"€|EUR|USD|US\$|GBP")


class ConstantsTests(unittest.TestCase):
    def test_values(self):
        by = {r.id: r for r in inputs_constants.INPUTS}
        self.assertEqual(len(by), 14)
        for k, v in EXPECTED.items():
            self.assertAlmostEqual(by[k].published_value, v, delta=1e-12)

    def test_shape(self):
        for r in inputs_constants.INPUTS:
            self.assertEqual(r.section, "Constants")
            self.assertIsNone(r.conversion_ref)
            self.assertFalse(MONEY.search(r.published_unit + r.model_unit))
            if r.id in EXPECTED:
                self.assertEqual(r.status, Status.ASSUMPTION)
                self.assertTrue(r.rationale.strip())

    def test_helpers(self):
        s = scalar("A_B", "Constants", "d", 1.0, "factor", None, "factor",
                   NA, None, Status.ASSUMPTION, "r")
        self.assertEqual(s.kind, Kind.SCALAR)
        p = series("A_C", "Constants", "d", [1.0, 2.0], "factor", None,
                   "factor", NA, None, Status.ASSUMPTION, "r")
        self.assertEqual(p.kind, Kind.SERIES)
        self.assertIsNone(p.published_value)
        self.assertEqual(p.series, (1.0, 2.0))


class AggregatorTests(unittest.TestCase):
    def test_concat(self):
        self.assertEqual(INPUTS, sum((m.INPUTS for m in MODS), ()))
        self.assertEqual(SOURCES, sum((m.SOURCES for m in MODS), ()))

    def test_unique(self):
        ids = [r.id for r in INPUTS]
        self.assertEqual(ids.count("Const_None"), 1)
        self.assertEqual(ids.count("Time_FirstYear"), 1)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
