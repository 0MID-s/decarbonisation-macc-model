"""Date-axis post-process: MACC charts carry c:auto=0, rest is untouched."""
import io
import re
import unittest
import zipfile

import build
from xl.postprocess import PostprocessError, patch_date_axis


def _raw_unpatched():
    """Rebuild the workbook bytes as XlsxWriter wrote them (auto=1)."""
    orig = build.patch_date_axis
    try:
        build.patch_date_axis = lambda data, expected_charts: data
        data, _ = build.build_bytes("main", build.load_dataset("config"))
    finally:
        build.patch_date_axis = orig
    return data


class DateAxisPostprocess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _raw_unpatched()
        cls.data, _ = build.build_bytes("main", build.load_dataset("config"))

    def _date_charts(self, data):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return [z.read(n).decode("utf-8") for n in z.namelist()
                    if re.match(r"xl/charts/chart\d+\.xml$", n)
                    and "<c:dateAx>" in z.read(n).decode("utf-8")]

    def test_raw_has_auto_one_built_has_auto_zero(self):
        for x in self._date_charts(self.raw):
            self.assertIn('<c:auto val="1"/>', x)
        charts = self._date_charts(self.data)
        self.assertEqual(len(charts), 3)  # chart A + zoom + Dashboard MACC
        for x in charts:
            ax = re.search(r"<c:dateAx>.*?</c:dateAx>", x, re.S).group(0)
            self.assertIn('<c:auto val="0"/>', ax)
            self.assertNotIn('<c:auto val="1"/>', ax)

    def test_categories_reference_macc_column_e(self):
        for x in self._date_charts(self.data):
            cats = re.findall(r"<c:cat>.*?<c:f>(.*?)</c:f>", x)
            self.assertTrue(cats)
            for f in cats:
                self.assertRegex(f, r"^MACC!\$E\$\d+:\$E\$\d+$")

    def test_idempotent_and_other_members_identical(self):
        again = patch_date_axis(self.data, 3)
        a = zipfile.ZipFile(io.BytesIO(self.data))
        b = zipfile.ZipFile(io.BytesIO(again))
        self.assertEqual(a.namelist(), b.namelist())
        for n in a.namelist():
            self.assertEqual(a.read(n), b.read(n), n)
        r = zipfile.ZipFile(io.BytesIO(self.raw))
        self.assertEqual(r.namelist(), a.namelist())
        for n in r.namelist():
            if n.startswith("xl/charts/chart") and "<c:dateAx>" in \
                    r.read(n).decode("utf-8"):
                continue
            self.assertEqual(r.read(n), a.read(n), n)
            self.assertEqual(r.getinfo(n).compress_type,
                             a.getinfo(n).compress_type)

    def test_wrong_chart_count_fails(self):
        with self.assertRaises(PostprocessError):
            patch_date_axis(self.raw, 4)

    def test_macc_chart_labels_are_short_names(self):
        import openpyxl
        from config.measures_catalog import MEASURES
        wb = openpyxl.load_workbook(io.BytesIO(self.data), data_only=True)
        ws = wb["MACC"]
        shorts = set(m.short for m in MEASURES)
        self.assertEqual(len(shorts), len(MEASURES))
        vals = [ws["H%d" % r].value for r in range(59, 65)]
        self.assertEqual(set(vals), shorts)


if __name__ == "__main__":
    unittest.main()
