"""Chart XML checks for the MACC factories, built without build.py."""
import io
import re
import unittest
import zipfile

import xlsxwriter

from checkmodel import macc_reference as ref
from tests.fixtures.synthetic import SYNTHETIC_MEASURES, SYNTHETIC_REFERENCE_PRICE
from xl.cells import CellWriter
from xl.charts import (BridgeLayout, TornadoLayout, bridge_chart,
                       tornado_chart, macc_area_chart,
                       macc_column_chart)
from xl.macc import write_macc_a_block, write_macc_c_block
from xl.styles import Styles

OPTIONS = {"in_memory": True, "strings_to_formulas": False,
           "strings_to_urls": False, "strings_to_numbers": False}


def _cat_values(xml):
    cat = re.search(r"<c:cat>(.*?)</c:cat>", xml, re.S).group(1)
    return [float(v) for v in re.findall(r"<c:v>([^<]*)</c:v>", cat)]


class Charts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, OPTIONS)
        styles, cells = Styles(wb), CellWriter(wb)
        wsa = wb.add_worksheet("MACC_A")
        wsc = wb.add_worksheet("MACC_C")
        srt = ref.rank_measures(SYNTHETIC_MEASURES)
        a = write_macc_a_block(cells, styles, wsa, SYNTHETIC_MEASURES,
                               SYNTHETIC_REFERENCE_PRICE)
        c = write_macc_c_block(cells, styles, wsc, a, srt)
        wsa.insert_chart("N6", macc_area_chart(wb, a))
        wsc.insert_chart("L6", macc_column_chart(wb, c))
        wb.close()
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
            cls.names = sorted(n for n in z.namelist()
                               if n.startswith("xl/charts/chart"))
            cls.xml = [z.read(n).decode("utf-8") for n in cls.names]
        cls.points = ref.macc_a_points(srt)

    def test_two_parts_and_area_structure(self):
        self.assertEqual(len(self.names), 2)
        area = self.xml[0]
        self.assertIn("<c:areaChart>", area)
        self.assertIn("<c:dateAx>", area)
        self.assertIn("<c:lineChart>", area)
        self.assertNotIn('<c:grouping val="stacked"/>', area)
        self.assertNotIn("percentStacked", area)
        a_part = area.split("<c:lineChart>")[0]
        self.assertEqual(a_part.count("<c:ser>"), 6)
        self.assertEqual(area.split("<c:lineChart>")[1].count("<c:ser>"), 1)

    def test_column_structure(self):
        col = self.xml[1]
        self.assertIn("<c:barChart>", col)
        self.assertIn('<c:gapWidth val="0"/>', col)
        self.assertIn('<c:overlap val="100"/>', col)
        self.assertEqual(col.count("<c:ser>"), 6)

    def test_x_cache_equals_reference(self):
        self.assertEqual(_cat_values(self.xml[0]),
                         [float(p[3]) for p in self.points])


class BridgeChart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, OPTIONS)
        ws = wb.add_worksheet("Exposure")
        layout = BridgeLayout(
            "Exposure", 3, 10, 1, 5, 6,
            (("Total", 7, 8, "#595959", 15, 16),
             ("Cost saving", 9, 10, "#009E73", 17, 18),
             ("Cost increase", 11, 13, "#D55E00", 19, 20)), 14, 2)
        ws.insert_chart("B20", bridge_chart(wb, layout, "=Exposure!$D$1"))
        wb.close()
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
            names = [n for n in z.namelist() if n.startswith("xl/charts/chart")]
            cls.xml = z.read(names[0]).decode("utf-8")

    def test_stacked_column_with_invisible_bases(self):
        x = self.xml
        self.assertIn("<c:barChart>", x)
        self.assertIn('<c:grouping val="stacked"/>', x)
        sers = x.split("<c:ser>")[1:]
        self.assertEqual(len(sers), 8)
        for s in sers[:2]:
            self.assertIn("<a:noFill/>", s.split("<c:cat>")[0])

    def test_no_axis_bounds_or_date_axis(self):
        self.assertNotIn("<c:max ", self.xml)
        self.assertNotIn("<c:min ", self.xml)
        self.assertNotIn("<c:dateAx>", self.xml)

    def test_legend_keeps_one_entry_per_colour(self):
        self.assertEqual(self.xml.count("<c:legendEntry>"), 5)


class TornadoChart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, OPTIONS)
        ws = wb.add_worksheet("Sensitivity")
        layout = TornadoLayout("Sensitivity", 3, 13, 1, 3, 4)
        ws.insert_chart("G3", tornado_chart(wb, layout, "=Sensitivity!$D$1"))
        wb.close()
        with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
            names = [n for n in z.namelist() if n.startswith("xl/charts/chart")]
            cls.xml = z.read(names[0]).decode("utf-8")

    def test_horizontal_bars_overlapping_and_reversed(self):
        x = self.xml
        self.assertIn('<c:barDir val="bar"/>', x)
        self.assertIn('<c:overlap val="100"/>', x)
        self.assertIn('<c:orientation val="maxMin"/>', x)
        self.assertEqual(x.count("<c:ser>"), 2)

    def test_no_axis_bounds_or_date_axis(self):
        self.assertNotIn("<c:max ", self.xml)
        self.assertNotIn("<c:min ", self.xml)
        self.assertNotIn("<c:dateAx>", self.xml)


if __name__ == "__main__":
    unittest.main()
