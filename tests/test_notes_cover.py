"""Disclaimer, Cover and Notes shell tests (BASE-06, D-33)."""
import dataclasses
import io
import re
import unittest

import openpyxl

import build
from config.schema import Status
from xl.sheets.common import FICTITIOUS_NOTE, disclaimer_text

EXPECTED = ("‘Maison Veritas’ is a fictitious company. Its baseline "
            "is a representative Belgian NACE C20 mid-sized manufacturer "
            "derived from official Eurostat statistics (sbs_sc_ovw, "
            "nrg_bal_c, env_ac_ainah_r2, retrieved %s). It does not "
            "represent any real company.")


class Notes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = build.load_dataset("config")
        data, _ = build.build_bytes("main", cls.ds)
        cls.wb = openpyxl.load_workbook(io.BytesIO(data))

    def test_disclaimer_exact(self):
        latest = max(s.retrieved for s in self.ds.sources
                     if s.id in ("Src_EurostatSBS", "Src_EurostatEnergyBalance",
                                 "Src_EurostatAirAccounts"))
        self.assertEqual(disclaimer_text(self.ds.sources),
                         EXPECTED % latest.isoformat())

    def test_fallback_for_missing_sources(self):
        fx = build.load_dataset("fixtures")
        self.assertEqual(disclaimer_text(fx.sources), FICTITIOUS_NOTE)

    def test_cover_and_notes_same_string(self):
        want = disclaimer_text(self.ds.sources)
        self.assertEqual(self.wb["Cover"]["B5"].value, want)
        self.assertEqual(self.wb["Notes"]["B5"].value, want)

    def test_headings(self):
        vals = [c.value for row in self.wb["Notes"].iter_rows() for c in row]
        for h in ("About this model", "Data scope and conventions",
                  "Limitations", "Exclusions", "Carbon price notes",
                  "Transcribed inputs (D-14 route 3)", "Version log"):
            self.assertIn(h, vals)

    def _text(self):
        return "\n".join(str(c.value) for row in self.wb["Notes"].iter_rows()
                         for c in row if c.value is not None)

    def test_transcribed_list_generated(self):
        t = self._text()
        for r in self.ds.inputs:
            if (r.note.startswith("Transcribed")
                    or r.rationale.startswith(("Transcribed",
                                           "Unverified transcription"))):
                self.assertIn(r.id + ":", t)
        self.assertIn("Carbon_EUA_Avg2025", t)

    def test_no_projection_wording(self):
        self.assertIn("Not captured: no official projection located on "
                      "allowlisted sources (see RESEARCH 3.11)", self._text())

    def test_projection_captured_wording(self):
        from xl.sheets.notes import ets2_projection_line
        rec = dataclasses.replace(
            [r for r in self.ds.inputs if r.id == "Carbon_EUA_Avg2025"][0],
            id="Carbon_ETS2_Proj_2030")
        line = ets2_projection_line(self.ds.inputs + (rec,), self.ds.sources)
        self.assertIn("captured as data for Phase 4", line)
        self.assertIn("Carbon_ETS2_Proj_2030", line)

    def test_flat_grid_deviation_stated(self):
        self.assertIn("DATA-05", self._text())
        self.assertIn("D-23", self._text())

    def test_no_formula_leading_chars(self):
        for row in self.wb["Notes"].iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    self.assertNotIn(c.value[:1], "=+-@")

    def test_prose_has_no_input_values(self):
        import xl.sheets.notes as nt
        from checkmodel.baseline_reference import model_values
        vals = set(model_values(self.ds.inputs).values())
        prose = " ".join(nt.ABOUT + nt.CONVENTIONS + nt.LIMITATIONS
                         + nt.EXCLUSIONS
                         + (nt.legal_status_note(self.ds.inputs),))
        prose = re.sub(r"(Phase|Scope) \d", "", prose)
        for tok in re.findall(r"(?<![\w.-])\d+(?:\.\d+)?(?![\w.-])", prose):
            x = float(tok)
            if 1900 <= x <= 2100:
                continue
            self.assertNotIn(x, vals, tok)

    def test_legal_status_note_follows_config(self):
        """IN-05: the Notes legal paragraph is generated from the statuses."""
        import xl.sheets.notes as nt
        from config.schema import Status
        text = nt.legal_status_note(self.ds.inputs)
        self.assertIn(" ".join(text.split()), " ".join(self._text().split()))
        legal = [r for r in self.ds.inputs
                 if r.id.startswith(nt.LEGAL_PREFIXES)
                 or r.id in nt.LEGAL_EXTRA_IDS]
        self.assertGreaterEqual(len(legal), 16)
        head, _, tail = text.partition("Analyst assumptions")
        for r in legal:
            self.assertIn(r.id, head if r.status is Status.SOURCED else tail,
                          r.id)
        self.assertIn("Dir. (EU) 2023/959 as enacted", text)
        self.assertIn("original 2003 Annex I wording", text)


if __name__ == "__main__":
    unittest.main()
