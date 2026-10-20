"""Value and provenance tests for the Finance and Carbon prices sections."""
import os
import re
import unittest

from config.inputs import INPUTS
from config.sources import SOURCES
from config.schema import Status

BY_ID = {r.id: r for r in INPUTS}
FIN = [r for r in INPUTS if r.section == "Finance"]
CAR = [r for r in INPUTS if r.section == "Carbon prices"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        for i in ("Fin_InflationLongRun", "Fin_HICP_EA_Sep2026"):
            self.assertEqual(BY_ID[i].status, Status.SOURCED, i)
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
        self.assertEqual(r.status, Status.ASSUMPTION)
        self.assertTrue(r.rationale.startswith("Unverified transcription:"))
        self.assertIn("docs/DATA_LOG.md", r.rationale)
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

    @staticmethod
    def data_log_outcomes():
        """Outcome per legal id, parsed from the DATA_LOG table "Final
        outcomes after user paste" (WR-04: no hand-kept copy of the set)."""
        with open(os.path.join(ROOT, "docs", "DATA_LOG.md")) as f:
            log = f.read()
        start = log.index("### Final outcomes after user paste")
        end = log.find("\n## ", start)
        section = log[start:end if end > 0 else len(log)]
        out = {}
        for m in re.finditer(r"^\| ((?:Carbon|Base)_[^|]*?) \| "
                             r"(VERIFIED|NOT READ|MISMATCH)", section, re.M):
            cell, outcome = m.group(1), m.group(2)
            ids = [x.strip() for x in cell.split(",")]
            stem = ids[0].rsplit("_", 1)[0]
            for x in ids:
                full = x if not x.startswith("_") else stem + x
                if full in out:
                    raise AssertionError("duplicate DATA_LOG row for " + full)
                out[full] = outcome
        return out

    def test_legal_status_follows_data_log(self):
        legal = [r for r in CAR if r.id.startswith(("Carbon_ETS2_", "Carbon_ETS1_"))]
        self.assertGreaterEqual(len(legal), 15)
        outcomes = self.data_log_outcomes()
        verified = {i for i, o in outcomes.items() if o == "VERIFIED"}
        # every legal record has a logged outcome, and Sourced <=> VERIFIED
        self.assertLessEqual({r.id for r in legal}, set(outcomes))
        for i in outcomes:
            self.assertIn(i, BY_ID, "DATA_LOG row for unknown id " + i)
        sourced = {i for i in outcomes if BY_ID[i].status is Status.SOURCED}
        self.assertEqual(sourced, verified)
        self.assertGreaterEqual(len(verified), 1)
        for r in legal:
            self.assertTrue(r.note.startswith("Transcribed:"), r.id)
            self.assertIn("docs/DATA_LOG.md", r.note, r.id)
            if r.id in verified:
                self.assertEqual(r.status, Status.SOURCED, r.id)
                self.assertIn("supplied by the user from EUR-Lex on 2026-",
                              r.note, r.id)
                self.assertIn("Text supplied by the user", r.rationale, r.id)
                self.assertTrue(r.rationale.startswith(
                    ("Text supplied by the user", "Text read: ")), r.id)
            else:
                self.assertEqual(r.status, Status.ASSUMPTION, r.id)
                self.assertTrue(r.rationale.startswith("Unverified transcription:"), r.id)
                self.assertIn("to be verified against the legal text", r.rationale, r.id)
                self.assertTrue(r.source_id, r.id)
            if r.status is Status.SOURCED:
                self.assertNotIn("Unverified", r.rationale, r.id)

    # DATA_LOG sections that log a source under a heading, not its Src_ id
    LOG_SECTION_ALIASES = {"Src_Damodaran": "### Damodaran Europe (D-42"}

    def test_every_sourced_input_is_logged(self):
        """WR-04, repo-wide: no Sourced record without a logged trace in
        DATA_LOG, by record id, source id or the source's log section."""
        with open(os.path.join(ROOT, "docs", "DATA_LOG.md")) as f:
            log = f.read()
        missing = []
        for r in INPUTS:
            if r.status is not Status.SOURCED:
                continue
            keys = (r.id, r.source_id, self.LOG_SECTION_ALIASES.get(r.source_id))
            if not any(k and k in log for k in keys):
                missing.append(r.id)
        self.assertEqual(missing, [])

    def test_read_wording_qualifier_visible(self):
        """WR-03: Sourced legal values read only in enacted or original
        wording say so first, in config and in DATA_LOG."""
        from config.inputs_carbon import READ_ANNEX_I_2003, READ_ETS2_ENACTED
        with open(os.path.join(ROOT, "docs", "DATA_LOG.md")) as f:
            log = f.read()
        exp = {"Carbon_ETS2_StabPrice": READ_ETS2_ENACTED,
               "Carbon_ETS2_StabMonths": READ_ETS2_ENACTED,
               "Carbon_ETS2_StabRelease": READ_ETS2_ENACTED,
               "Carbon_ETS2_TripleTrigger": READ_ETS2_ENACTED,
               "Carbon_ETS2_TripleRelease": READ_ETS2_ENACTED,
               "Carbon_ETS1_ThermalThresholdMW": READ_ANNEX_I_2003}
        for i, q in exp.items():
            r = BY_ID[i]
            self.assertEqual(r.status, Status.SOURCED, i)
            self.assertTrue(r.rationale.startswith("Text read: " + q), i)
            row = [ln for ln in log.splitlines()
                   if ln.startswith("| %s | VERIFIED" % i)]
            self.assertEqual(len(row), 1, i)
            self.assertIn("Text read: " + q, row[0], i)

    def test_threshold_sourced_from_original_wording(self):
        r = BY_ID["Carbon_ETS1_ThermalThresholdMW"]
        self.assertEqual(r.status, Status.SOURCED)
        self.assertIn("original 2003", r.rationale)

    def test_count(self):
        self.assertGreaterEqual(len(CAR), 16)


# Values typed from docs/DATA_LOG.md, sections "NGFS Phase V (D-40, D-43" and
# "Damodaran Europe (D-42" (threat T-02-36).
NGFS_LOG = {
    "CP": (23.28186044073566, (23.27705035642764, 23.31220235560375,
                               23.39144477859998, 23.52964512661944,
                               23.71263250865933, 23.94119902155565)),
    "NDC": (121.5670480013598, (216.911391375443, 215.9468030914937,
                                214.9804569215596, 213.8716366193923,
                                211.1302917041736, 206.8712342559588)),
    "NZ50": (152.3844736690992, (282.2098852376754, 452.7636315503082,
                                 623.9807303273395, 795.3846925061491,
                                 870.0502582689974, 898.2429363719594)),
}
NGFS_YEARS = (2030, 2035, 2040, 2045, 2050, 2055)


class NGFSAndDamodaranTests(unittest.TestCase):
    def test_ngfs_values_match_data_log(self):
        self.assertEqual(BY_ID["Carbon_NGFS_Y0Year"].published_value, 2025)
        for k, (y0, pts) in NGFS_LOG.items():
            s = BY_ID["Carbon_NGFS_" + k + "_Y0"]
            self.assertEqual(s.published_value, y0)
            r = BY_ID["Carbon_NGFS_" + k]
            self.assertEqual(r.series, tuple(zip(NGFS_YEARS, pts)))
            for x in (s, r):
                self.assertEqual(x.source_id, "Src_NGFSPhaseV")
                self.assertEqual(x.published_unit, "US$2010/tCO2")
                self.assertEqual(x.price_basis.label, "USD 2010 real")
                self.assertEqual(x.status, Status.SOURCED)

    def test_ngfs_source_pins_model_and_region(self):
        src = [s for s in SOURCES if s.id == "Src_NGFSPhaseV"][0]
        self.assertIn("REMIND-MAgPIE 3.3-4.8", src.dataset)
        self.assertIn("OECD & EU (R5)", src.dataset)
        self.assertIn("Price|Carbon", src.dataset)

    def test_damodaran_values(self):
        exp = {"Fin_CoC_ChemSpecialty": 7.811, "Fin_CoC_ChemBasic": 5.144,
               "Fin_CoC_ChemDiversified": 7.608}
        for i, v in exp.items():
            r = BY_ID[i]
            self.assertEqual((r.published_value, r.model_unit,
                              r.source_id, r.conversion_ref),
                             (v, "%", "Src_Damodaran", "Const_PctToFrac"))
            self.assertTrue(r.note.startswith("Transcribed"))
        self.assertIn("8.873%", BY_ID["Fin_CoC_ChemSpecialty"].note)
        self.assertIn("1.5%", BY_ID["Fin_CoC_ChemSpecialty"].rationale)

    def test_no_currency_adjustment(self):
        self.assertNotIn("Fin_CoC_CurrencyAdj", BY_ID)


if __name__ == "__main__":
    unittest.main()
