"""Tests for the read-only parse scripts. No network, no writes."""
import ast
import csv
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import xlsxwriter

from tools import parse_eurostat, parse_misc, parse_ngfs, parse_xlsx

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def run(mod, argv):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = mod.main(argv)
    return rc, out.getvalue()


class ParserTests(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.d = Path(self._t.name)

    def listing(self):
        return sorted(os.listdir(self.d))

    def check(self, mod, argv, expect_rc=0):
        before = self.listing()
        rc, out = run(mod, argv)
        self.assertEqual(rc, expect_rc)
        self.assertEqual(before, self.listing())
        return out

    def test_eurostat(self):
        p = self.d / "e.json"
        p.write_text(json.dumps({
            "id": ["geo", "time"], "size": [2, 2],
            "dimension": {"geo": {"category": {"index": {"BE": 0, "NL": 1}}},
                          "time": {"category": {"index": {"2022": 0, "2023": 1}}}},
            "value": {"0": 1.5, "3": 4.0}, "status": {"3": "p"}}))
        out = self.check(parse_eurostat, [str(p)])
        self.assertEqual(out.splitlines(), ["BE|2022 1.5 -", "NL|2023 4.0 p"])
        out = self.check(parse_eurostat, [str(p), "--filter", "geo=NL"])
        self.assertEqual(out.splitlines(), ["NL|2023 4.0 p"])

    def test_xlsx(self):
        p = self.d / "w.xlsx"
        wb = xlsxwriter.Workbook(str(p))
        wb.add_worksheet("One").write_row(0, 0, ["Natural gas", 0.18])
        s2 = wb.add_worksheet("Two")
        s2.write_row(0, 0, ["Diesel", 2.5])
        s2.write_row(1, 0, ["Natural gas", 9])
        wb.close()
        self.assertEqual(self.check(parse_xlsx, [str(p), "--list-sheets"]).split(), ["One", "Two"])
        out = self.check(parse_xlsx, [str(p), "--match", "natural", "--match", "gas"])
        self.assertIn("One!A1: Natural gas | 0.18", out)
        self.assertIn("Two!A2: Natural gas | 9", out)
        out = self.check(parse_xlsx, [str(p), "--sheet", "Two", "--match", "diesel"])
        self.assertEqual(out.strip(), "Two!A1: Diesel | 2.5")

    def test_pvgis(self):
        p = self.d / "pv.json"
        p.write_text(json.dumps({
            "inputs": {"mounting_system": {"fixed": {"slope": {"value": 10}}}},
            "outputs": {"totals": {"fixed": {"E_y": 942.09, "H(i)_y": 1200.0, "SD_y": 40.1}}}}))
        out = self.check(parse_misc, ["pvgis", str(p)])
        self.assertIn("E_y = 942.09", out)
        self.assertIn("H(i)_y = 1200.0", out)
        self.assertIn("SD_y = 40.1", out)
        self.assertIn("value = 10", out)

    def test_eea(self):
        p = self.d / "eea.csv"
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Country", "Year", "Intensity"])
            w.writerow(["Belgium", 2022, 154])
            w.writerow(["Netherlands", 2022, 310])
        out = self.check(parse_misc, ["eea", str(p), "--country", "Belgium"])
        self.assertIn("Year=2022", out)
        self.assertIn("Intensity=154", out)
        self.assertNotIn("310", out)

    def _ngfs(self, delim, suffix):
        p = self.d / ("n" + suffix)
        hdr = ["Model", "Scenario", "Region", "Variable", "Unit", "2020", "2030"]
        with open(p, "w", newline="") as f:
            w = csv.writer(f, delimiter=delim)
            w.writerow(hdr)
            w.writerow(["REMIND-MAgPIE 3.3-4.8", "Net Zero 2050", "World", "Price|Carbon", "US$2010/t CO2", 1, 100])
            w.writerow(["REMIND-MAgPIE 3.3-4.8 IntegratedPhysicalDamages (median)", "Net Zero 2050", "World", "Price|Carbon", "US$2010/t CO2", 2, 200])
            w.writerow(["REMIND-MAgPIE 3.3-4.8", "Net Zero 2050", "World", "Emissions|CO2", "Mt", 5, 5])
            w.writerow(["Copyright notice"])
        return p

    def test_ngfs_csv_and_tsv(self):
        for delim, suffix in ((",", ".csv"), ("\t", ".tsv")):
            p = self._ngfs(delim, suffix)
            out = self.check(parse_ngfs, [str(p), "--model", "REMIND-MAgPIE 3.3-4.8", "--region", "World"])
            lines = out.splitlines()
            self.assertEqual(len(lines), 2)
            self.assertIn("2030=100", lines[0])
            self.assertNotIn("Damages", lines[0])
            self.assertEqual(lines[1], "footer: Copyright notice")

    def test_ngfs_refusals(self):
        bad = self.d / "x.txt"
        bad.write_text("Model\tScenario\n")
        self.check(parse_ngfs, [str(bad)], expect_rc=1)
        nohdr = self.d / "y.csv"
        nohdr.write_text("a,b\n")
        self.check(parse_ngfs, [str(nohdr)], expect_rc=1)

    def test_no_build_imports(self):
        for f in TOOLS.glob("parse_*.py"):
            tree = ast.parse(f.read_text())
            for n in ast.walk(tree):
                names = []
                if isinstance(n, ast.Import):
                    names = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    names = [n.module or ""]
                for nm in names:
                    self.assertNotIn(nm.split(".")[0], ("config", "xl", "qa", "checkmodel"), f.name)


if __name__ == "__main__":
    unittest.main()
