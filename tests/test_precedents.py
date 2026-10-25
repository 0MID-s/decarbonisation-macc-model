"""Precedent walk tests (plan 04-06): ICP isolation proof (D-13)."""
import io
import unittest

import openpyxl
import xlsxwriter
from openpyxl.utils import range_boundaries

import build
from qa.precedents import PrecedentError, dependents, name_cells
from xl.cells import CellWriter


class Synthetic(unittest.TestCase):
    def _book(self, extra=None):
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        ws = wb.add_worksheet("S")
        cw = CellWriter(wb)
        ws.write("A1", 5)
        cw.formula(ws, 0, 1, "=A1+A1", None, value=10)
        cw.formula(ws, 0, 2, "=B1+1", None, value=11)
        ws.write("D1", 7)
        cw.define_name("Nm_B", "=S!$B$1")
        cw.formula(ws, 0, 4, "=Nm_B+Nm_B", None, value=30)
        if extra:
            extra(cw, ws)
        wb.close()
        return buf.getvalue()

    def test_transitive_and_names(self):
        d = dependents(self._book(), [("S", "A1")])
        self.assertEqual(d, {("S", "B1"), ("S", "C1"), ("S", "E1")})

    def test_unrelated_cell_excluded(self):
        self.assertEqual(dependents(self._book(), [("S", "D1")]), set())

    def test_dynamic_reference_refused(self):
        def extra(cw, ws):
            ws.write_formula("F1", "=OFFSET(A1,0,0)", None, 5)
        with self.assertRaises(PrecedentError):
            dependents(self._book(extra), [("S", "A1")])


class RealBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, _ = build.build_bytes("main", build.load_dataset("config"))
        cls.wb = openpyxl.load_workbook(io.BytesIO(cls.data))
        seed = name_cells(cls.data, "Carbon_ICP_Level")
        cls.deps = dependents(cls.data, seed)

    def _band(self):
        sheet, ref = self.wb.defined_names["Expo_ICP_Band"].attr_text.split("!")
        c1, r1, c2, r2 = range_boundaries(ref.replace("$", ""))
        return sheet, c1, r1, c2, r2

    def test_icp_reaches_only_its_band(self):
        self.assertTrue(self.deps)
        sheet, c1, r1, c2, r2 = self._band()
        for s, coord in self.deps:
            cell = self.wb[s][coord]
            self.assertEqual(s, sheet, (s, coord))
            self.assertTrue(r1 <= cell.row <= r2 and c1 <= cell.column <= c2,
                            "%s!%s is outside Expo_ICP_Band" % (s, coord))

    def test_cash_cells_not_dependent(self):
        cash = set()
        for nm in ("Expo_CumBAU_Sel", "Expo_DiscAvoided_Sel",
                   "Expo_Check_CashIsChannels"):
            cash.update(name_cells(self.data, nm))
        for key in ("CP", "NDC", "NZ50"):
            for case in ("BAU", "With"):
                cash.update(name_cells(self.data,
                                       "Expo_%s_Total_%s" % (case, key)))
        self.assertFalse(cash & self.deps)


if __name__ == "__main__":
    unittest.main()
