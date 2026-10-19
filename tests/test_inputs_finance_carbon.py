"""Value and provenance tests for the Finance and Carbon prices sections."""
import unittest

from config.inputs import INPUTS
from config.sources import SOURCES
from config.schema import Status

BY_ID = {r.id: r for r in INPUTS}
FIN = [r for r in INPUTS if r.section == "Finance"]
CAR = [r for r in INPUTS if r.section == "Carbon prices"]


class FinanceTests(unittest.TestCase):
    def test_count_and_hicp(self):
        self.assertGreaterEqual(len(FIN), 11)
        exp = {2010: 93.14, 2019: 104.80, 2020: 105.06, 2021: 107.78,
               2022: 116.82, 2023: 123.15, 2024: 126.07, 2025: 128.75}
        for y, v in exp.items():
            r = BY_ID["Fin_HICP_EA_%d" % y]
            self.assertEqual((r.published_value, r.model_unit, r.source_id),
                             (v, "index", "Src_EurostatHICP"))

    def test_inflation_and_fx(self):
        r = BY_ID["Fin_InflationLongRun"]
        self.assertEqual((r.published_value, r.model_unit, r.source_id),
                         (2.0, "%", "Src_ECBTarget"))
        self.assertEqual(BY_ID["Fin_HICP_EA_Sep2026"].published_value, 3.8)
        r = BY_ID["Fin_FX_USDperEUR_2010"]
        self.assertEqual(r.published_value, 1.3257)
        self.assertEqual(r.price_basis.label, "EUR 2010 nominal")

    def test_no_bls_or_ecb_fx(self):
        ids = set(BY_ID)
        self.assertFalse([i for i in ids if i.startswith("Fin_USCPI")])
        self.assertNotIn("Fin_EURUSD_2025", ids)
        for s in SOURCES:
            self.assertNotIn("bls.gov", s.url)

    def test_transcribed_notes(self):
        n = sum(1 for r in FIN if "Transcribed" in r.note)
        self.assertGreaterEqual(n, 2)


class CarbonTests(unittest.TestCase):
    def test_eua(self):
        r = BY_ID["Carbon_EUA_Avg2025"]
        self.assertEqual(r.published_value, 73.43)
        self.assertIn("73.45", r.note)
        self.assertEqual(r.price_basis.label, "EUR 2025 nominal")

    def test_ets2_values(self):
        exp = {"Carbon_ETS2_StartYear": 2028,
               "Carbon_ETS2_StartYearEnacted": 2027,
               "Carbon_ETS2_StabPrice": 45, "Carbon_ETS2_StabMonths": 2,
               "Carbon_ETS2_StabRelease": 20, "Carbon_ETS2_TripleTrigger": 3,
               "Carbon_ETS2_TripleRelease": 150,
               "Carbon_ETS1_ThermalThresholdMW": 20}
        for i, v in exp.items():
            self.assertEqual(BY_ID[i].published_value, v, i)
        self.assertEqual(BY_ID["Carbon_ETS2_StabPrice"].price_basis.label,
                         "EUR 2020 real")
        self.assertEqual(BY_ID["Carbon_ETS2_StartYear"].source_id,
                         "Src_Reg2026_667")

    def test_scope_flags(self):
        for k in ("Gas", "LPG", "Naphtha", "OtherFuels", "FleetDiesel"):
            self.assertEqual(BY_ID["Carbon_ETS2_Scope_" + k].published_value, 1)
        for k in ("Elec", "Heat"):
            self.assertEqual(BY_ID["Carbon_ETS2_Scope_" + k].published_value, 0)

    def test_legal_notes_name_text_version(self):
        legal = [r for r in CAR if r.id.startswith(("Carbon_ETS2_", "Carbon_ETS1_"))]
        self.assertGreaterEqual(len(legal), 15)
        for r in legal:
            self.assertTrue(r.note.startswith("Transcribed:"), r.id)
            self.assertIn("text read:", r.note, r.id)
            self.assertEqual(r.status, Status.SOURCED)

    def test_count(self):
        self.assertGreaterEqual(len(CAR), 16)


if __name__ == "__main__":
    unittest.main()
