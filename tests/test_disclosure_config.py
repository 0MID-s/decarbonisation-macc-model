"""Disclosure mapping data tests (plan 05-06, D-01 to D-05)."""
import io
import unittest

import openpyxl

import build
from checkmodel.exposure_reference import STATES
from checkmodel.outputs_reference import linked_value
from config import disclosure as d
from config.security import host_allowed

DEFAULT = ("Market-based", "Central", "Off")


class DisclosureConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, _ = build.build_bytes("main", build.load_dataset("config"))
        wb = openpyxl.load_workbook(io.BytesIO(data))
        cls.names = set(wb.defined_names.keys())
        cls.refs = " | ".join(r.reference for r in d.DISCLOSURE_ROWS)

    def test_strength_and_status_values(self):
        for r in d.DISCLOSURE_ROWS:
            self.assertIn(r.strength, ("Direct", "Supports", "Not covered"), r)
            self.assertIn(r.status, d.STATUSES, r)

    def test_ref_ids(self):
        for r in d.DISCLOSURE_ROWS:
            if r.status == "n/a":
                self.assertEqual(r.ref_id, "")
            else:
                self.assertIn(r.ref_id, d.STD_REFS, r)
        for ref in d.STD_REFS.values():
            self.assertTrue(host_allowed(ref.url), ref.url)
            self.assertEqual(ref.retrieved, "2026-10-25")

    def test_required_references_present(self):
        s2 = [r.reference for r in d.DISCLOSURE_ROWS
              if r.standard == "IFRS S2"]
        for ref in ("14", "15", "16", "17-21", "22", "29(a)(v)", "29(e)",
                    "29(f)(i)", "29(f)(ii)"):
            self.assertTrue(any(ref in x for x in s2), ref)
        esrs = [r.reference for r in d.DISCLOSURE_ROWS
                if r.standard.startswith("ESRS")]
        for ref in ("E1-1", "E1-7", "E1-8", "E1-10", "E1-11"):
            self.assertTrue(any(x.startswith(ref) for x in esrs), ref)
        for r in d.DISCLOSURE_ROWS:
            if r.standard.startswith("ESRS") and "energy" in r.requirement.lower():
                self.assertTrue(r.reference.startswith("E1-7"), r)

    def test_not_covered_topics(self):
        nc = [r for r in d.DISCLOSURE_ROWS if r.strength == "Not covered"]
        self.assertGreaterEqual(len(nc), 5)
        text = " ".join(r.requirement.lower() + " " + r.reference for r in nc)
        for topic in ("scope 3", "physical", "governance", "remuneration",
                      "assurance"):
            self.assertIn(topic, text)
        assur = [r for r in nc if "assurance" in r.requirement.lower()]
        self.assertEqual(assur[0].status, "n/a")
        self.assertEqual(assur[0].reference, d.NONE)

    def test_paraphrase_bound(self):
        for r in d.DISCLOSURE_ROWS:
            self.assertLessEqual(len(r.requirement), 160, r.requirement)
            for q in ('"', "'", "“", "”", "‘", "’"):
                self.assertNotIn(q, r.requirement)

    def test_output_names_exist_and_link(self):
        for r in d.DISCLOSURE_ROWS:
            for n in r.output_names:
                self.assertIn(n, self.names, n)
        for n in d.value_names():
            self.assertIn(n, d.OUTPUT_UNITS, n)
            self.assertIsNotNone(linked_value(n, DEFAULT), n)

    def test_values_defined_in_every_state(self):
        for st in STATES[:3]:
            for n in d.value_names():
                linked_value(n, st)

    def test_legal_basis_flag(self):
        ref = d.STD_REFS["Std_ESRS_Rev2026"]
        self.assertIn("2026/1563", ref.edition)
        self.assertIn("EUR-Lex page not machine-readable", ref.status_note)
        self.assertIn("EUR-Lex page not machine-readable",
                      d.STD_REFS["Std_EURLex_1563"].status_note)

    def test_corrections(self):
        txt = " ".join(" ".join(c) for c in d.CORRECTIONS)
        for s in ("E1-7", "E1-8", "E1-10", "E1-11", "2026/1560", "2026/1563",
                  "Std_"):
            self.assertIn(s, txt)

    def test_no_e1_5_energy(self):
        for r in d.DISCLOSURE_ROWS:
            if r.standard.startswith("ESRS"):
                self.assertFalse(r.reference.startswith("E1-5")
                                 and "energy" in r.requirement.lower())


if __name__ == "__main__":
    unittest.main()
