"""Value, order and provenance tests for the Baseline and Energy prices sections."""
import unittest

from config.inputs import INPUTS
from config.schema import Status

BY_ID = {r.id: r for r in INPUTS}
BASE = [r for r in INPUTS if r.section == "Baseline"]

BASE_EXPECTED = [
    ("Base_RefYear", 2024), ("Base_SBS_C20M_Ent", 110),
    ("Base_SBS_C20M_Persons", 13960), ("Base_SBS_C20M_VA", 2536.48),
    ("Base_SBS_C20M_Turnover", 12396.76), ("Base_SBS_C20_VA", 8911.42),
    ("Base_SBS_C21_VA", 16919.86), ("Base_SBS_C20_Turnover", 42576.38),
    ("Base_SBS_C21_Turnover", 48554.13), ("Base_NRG_IncludesC21", 1),
    ("Base_NRG_Total", 162119.849), ("Base_NRG_Gas", 62515.885),
    ("Base_NRG_Elec", 48458.52), ("Base_NRG_Heat", 8030.8),
    ("Base_NRG_LPG", 11356.73), ("Base_NRG_Naphtha", 29361.1),
    ("Base_NRG_GasOil", 1143.8), ("Base_Air_C20_GHG", 9173823.08),
    ("Base_Air_C21_GHG", 238898.76), ("Base_Fleet_Vehicles", 10),
    ("Base_Fleet_KmPerVehicle", 25000), ("Base_Fleet_gCO2PerKm", 184.9),
]


class BaselineTests(unittest.TestCase):
    def test_order_and_values(self):
        self.assertEqual([r.id for r in BASE], [i for i, _ in BASE_EXPECTED])
        for rid, val in BASE_EXPECTED:
            self.assertEqual(BY_ID[rid].published_value, val, rid)

    def test_nrg_units(self):
        nrg = [r for r in BASE if r.id.startswith("Base_NRG_")
               and r.conversion_ref == "Const_TJ_to_MWh"]
        self.assertEqual(len(nrg), 7)
        for r in nrg:
            self.assertEqual((r.published_unit, r.model_unit), ("TJ", "MWh"))

    def test_status(self):
        for r in BASE:
            exp = (Status.ASSUMPTION if r.id in (
                "Base_Fleet_Vehicles", "Base_Fleet_KmPerVehicle")
                else Status.SOURCED)
            self.assertEqual(r.status, exp, r.id)
            if exp is Status.ASSUMPTION:
                self.assertTrue(r.rationale)


if __name__ == "__main__":
    unittest.main()
