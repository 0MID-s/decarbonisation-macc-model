"""Phase 3 inputs (03-04): values, statuses, sources and the catalogue."""
import re
import unittest
from pathlib import Path

from config import inputs_constants, inputs_measures, inputs_prices
from config import measures_catalog
from config.schema import Status

ALL = (inputs_measures.INPUTS + inputs_prices.INPUTS
       + inputs_constants.INPUTS)
BY = dict((r.id, r) for r in ALL)
S, A = Status.SOURCED, Status.ASSUMPTION

# id: (value, status, source_id, published_unit)
EXPECT = {
    "Price_DieselBE_WithTax": (1658.59, S, "Src_EUOilBulletin", "EUR/1000 l"),
    "Price_DieselBE_VAT": (21, S, "Src_EUOilBulletin", "per cent"),
    "Meas_LED_ZMCapex": (252.224, S, "Src_RVOEML", "EUR per unit"),
    "Meas_LED_ZMSaving": (215.75, S, "Src_RVOEML", "kWh/yr per unit"),
    "Meas_VSD_ZMCapex": (5521.60, S, "Src_RVOEML", "EUR per unit"),
    "Meas_Boiler_IndirectCapex": (0.23, S, "Src_DEAProcessHeat", "M EUR/MW"),
    "Meas_HP_FullLoadHours": (8000, S, "Src_PBLSDE2026", "h/yr"),
    "Meas_HP_HeatHighPJ": (25.3, S, "Src_JRCHeat", "PJ"),
    "Meas_HP_HeatMedPJ": (12.5, S, "Src_JRCHeat", "PJ"),
    "Meas_HP_HeatLowPJ": (21.0, S, "Src_JRCHeat", "PJ"),
    "Meas_PV_RoofArea": (4.479, S, "Src_DEAElectricity", "1000 m2/MWp"),
    "Meas_RC_GOPrice": (2.05, S, "Src_WalloniaMarket", "EUR/GO"),
    "Meas_LED_LightingShare": (6, A, None, "per cent"),
    "Meas_LED_Coverage": (50, A, None, "per cent"),
    "Meas_LED_SavingRate": (50, A, None, "per cent"),
    "Meas_VSD_MotorShare": (10, A, None, "per cent"),
    "Meas_VSD_Coverage": (50, A, None, "per cent"),
    "Meas_VSD_SavingRate": (15, A, None, "per cent"),
    "Meas_PV_Size": (1000, A, None, "kWp"),
    "Meas_Fleet_ChargerCapex": (2000, A, None, "EUR per vehicle"),
    "Meas_Fleet_MaintSaving": (0.03, A, None, "EUR/km"),
    "Meas_Fleet_DieselVanPrice": (35000, A, None, "EUR per vehicle"),
    "Meas_RC_Term": (10, A, None, "years"),
}
NEW_SOURCES = ("Src_EUOilBulletin", "Src_JRCHeat", "Src_WalloniaMarket")


class Phase3InputTests(unittest.TestCase):
    def test_unique_ids(self):
        ids = [r.id for r in ALL]
        self.assertEqual(len(ids), len(set(ids)))

    def test_values(self):
        for id_, (val, st, src, unit) in EXPECT.items():
            r = BY[id_]
            self.assertAlmostEqual(r.published_value, val, places=9, msg=id_)
            self.assertEqual((r.status, r.source_id, r.published_unit),
                             (st, src, unit), id_)

    def test_assumptions_have_rationale(self):
        for r in ALL:
            if r.id.startswith(("Meas_", "Price_Diesel")) \
                    and r.status == A:
                self.assertTrue(r.rationale.strip(), r.id)

    def test_new_sources_used(self):
        used = set(r.source_id for r in ALL)
        reg = set(s.id for s in inputs_measures.SOURCES
                  + inputs_prices.SOURCES)
        for sid in NEW_SOURCES:
            self.assertIn(sid, reg)
            self.assertIn(sid, used)

    def test_subsidies_zero(self):
        subs = [r for r in ALL if r.id.endswith("_Subsidy")]
        self.assertEqual(len(subs), 6)
        for r in subs:
            self.assertEqual(r.published_value, 0)
            self.assertEqual(r.status, A)
            self.assertIn("D-15", r.rationale)

    def test_catalogue(self):
        self.assertEqual(measures_catalog.MEASURE_KEYS,
                         ("LED", "VSD", "HP", "Fleet", "PV", "RC"))
        for m in measures_catalog.MEASURES:
            self.assertTrue(m.barrier_note.startswith("Analyst commentary:"))
            self.assertTrue(m.name)

    def test_catalogue_imports(self):
        src = Path(measures_catalog.__file__).read_text()
        self.assertIsNone(re.search(r"^(from|import) (xl|checkmodel)", src,
                                    re.M))


if __name__ == "__main__":
    unittest.main()
