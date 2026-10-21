"""Value, order and provenance tests for the Baseline and Energy prices sections."""
import re
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
            # Base_NRG_IncludesC21: DATA_LOG WR-02 outcome NOT READ
            exp = (Status.ASSUMPTION if r.id in (
                "Base_Fleet_Vehicles", "Base_Fleet_KmPerVehicle",
                "Base_NRG_IncludesC21")
                else Status.SOURCED)
            self.assertEqual(r.status, exp, r.id)
            if exp is Status.ASSUMPTION:
                self.assertTrue(r.rationale)


class TestDataLogCitations(unittest.TestCase):
    # sources logged under a heading that is not their Src_ id
    LOG_SECTION_ALIASES = {"Src_Damodaran": "### Damodaran Europe (D-42"}

    @staticmethod
    def _log_text_for(log, sid, alias=None):
        """DATA_LOG text about one source: its "## Src_x" section, any line
        naming the id, and its alias section if any."""
        parts = [ln for ln in log.splitlines() if sid in ln]
        for head in ("## " + sid + "\n", (alias + "") if alias else None):
            if head and head in log:
                start = log.index(head)
                nxt = re.search(r"^##", log[start + len(head):], re.M)
                end = start + len(head) + (nxt.start() if nxt else len(log))
                parts.append(log[start:end])
        return "\n".join(parts)

    def test_no_dangling_edition_dates(self):
        """IN-02: every "updated YYYY-MM-DD" in an edition must appear in the
        DATA_LOG text for the same source, not merely somewhere in the log."""
        import os
        from config.sources import SOURCES
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log = open(os.path.join(root, "docs", "DATA_LOG.md")).read()
        n = 0
        for s in SOURCES:
            self.assertNotIn("per DATA_LOG", s.edition, s.id)
            for d in re.findall(r"updated (\d{4}-\d{2}-\d{2})", s.edition):
                text = self._log_text_for(log, s.id,
                                          self.LOG_SECTION_ALIASES.get(s.id))
                self.assertIn(d, text, s.id)
                n += 1
        self.assertGreaterEqual(n, 1)

    def test_reread_records_carry_no_stale_or_unlogged_text(self):
        """WR-05: no unlogged figure, and no "not re-read" clause beside a
        "re-read" rationale."""
        for i in ("Base_Fleet_gCO2PerKm", "Fin_InflationLongRun",
                  "Fin_HICP_EA_Sep2026"):
            r = BY_ID[i]
            self.assertEqual(r.status, Status.SOURCED, i)
            text = r.rationale + " " + r.note
            self.assertIn("re-read 2026-10-20", text.lower(), i)
            for stale in ("not re-read", "MEDIUM confidence",
                          "battery-electric", "10%"):
                self.assertNotIn(stale, text, i)


PRICE = [r for r in INPUTS if r.section == "Energy prices"]
EB = ["IA", "IB", "IC", "ID", "IE", "IF", "IG"]
GB = ["I1", "I2", "I3", "I4", "I5", "I6"]
ELEC_V = {"S1": [0.3138, 0.2314, 0.1940, 0.1659, 0.1348, 0.1155, 0.0982],
          "S2": [0.2808, 0.2158, 0.1866, 0.1571, 0.1311, 0.1141, 0.0920],
          "26S1": [0.3172, 0.2318, 0.1902, 0.1600, 0.1332, 0.1148, 0.1014]}
GAS_V = {"S1": [0.0749, 0.0689, 0.0505, 0.0428, 0.0415, 0.0424],
         "S2": [0.0700, 0.0603, 0.0481, 0.0399, 0.0376, 0.0345],
         "26S1": [0.0677, 0.0548, 0.0439, 0.0389, 0.0389, 0.0392]}


class PriceTests(unittest.TestCase):
    def test_count_and_contiguous_order(self):
        self.assertEqual(len(PRICE), 55)
        ids = [r.id for r in INPUTS]
        first = ids.index("Price_ElecLower_IA")
        self.assertEqual(ids[first:first + 55], [r.id for r in PRICE])
        exp = []
        for pre, bands, in (("Elec", EB), ("Gas", GB)):
            exp += ["Price_%sLower_%s" % (pre, b) for b in bands]
            for k in ("S1", "S2", "26S1"):
                exp += ["Price_%s%s_%s" % (pre, k, b) for b in bands]
        exp += ["Price_RealEscalation", "Price_DieselBE_WithTax",
                "Price_DieselBE_VAT"]
        self.assertEqual([r.id for r in PRICE], exp)

    def test_lower_bounds(self):
        self.assertEqual([BY_ID["Price_ElecLower_" + b].published_value
                          for b in EB], [0, 20, 500, 2000, 20000, 70000, 150000])
        self.assertEqual([BY_ID["Price_GasLower_" + b].published_value
                          for b in GB], [0, 1000, 10000, 100000, 1000000, 4000000])

    def test_values_units_basis(self):
        for pre, bands, tab in (("Elec", EB, ELEC_V), ("Gas", GB, GAS_V)):
            for k, vals in tab.items():
                for b, v in zip(bands, vals):
                    r = BY_ID["Price_%s%s_%s" % (pre, k, b)]
                    self.assertEqual(r.published_value, v, r.id)
                    self.assertEqual((r.published_unit, r.conversion_ref,
                                      r.model_unit),
                                     ("EUR/kWh", "Const_kWh_per_MWh", "EUR/MWh"))
                    self.assertEqual(r.price_basis.year,
                                     2026 if k == "26S1" else 2025)
                    self.assertEqual(r.price_basis.real_nominal, "nominal")

    def test_escalation(self):
        r = BY_ID["Price_RealEscalation"]
        self.assertEqual((r.published_value, r.published_unit, r.model_unit,
                          r.conversion_ref, r.status),
                         (0.0, "per cent", "%", "Const_PctToFrac",
                          Status.ASSUMPTION))


if __name__ == "__main__":
    unittest.main()
