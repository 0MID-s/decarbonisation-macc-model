"""Mutation tests for the default-deny OOXML scan (D-13, D-14, SET-03).

No real macro is created or run: mutated copies only add inert bytes/parts.
"""
import io
import unittest
import warnings
import zipfile

import xlsxwriter

from qa.scan import PART_ALLOWLIST, ScanError, part_names, scan_or_raise, scan_xlsx_bytes

OPTS = {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}


def build(fn=None, chart=True, link=True):
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, OPTS)
    ws = wb.add_worksheet("Sheet1")
    ws.write_number("A1", 1)
    ws.write_number("A2", 2)
    ws.write_string("B1", "Hello")
    if link:
        ws.write_url("C1", "https://ec.europa.eu/eurostat/")
    if chart:
        ch = wb.add_chart({"type": "area"})
        ch.add_series({"values": "=Sheet1!$A$1:$A$2"})
        ws.insert_chart("E2", ch)
    if fn:
        fn(wb, ws)
    wb.close()
    return buf.getvalue()


def clean_workbook_bytes():
    return build()


def mutate(data, add=None, replace=None, dup=None):
    """Rebuild the zip; add={name: bytes}, replace={name: callable(bytes)->bytes},
    dup={name: bytes} appends a second entry with an existing name."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(
            out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            raw = zin.read(info.filename)
            if replace and info.filename in replace:
                raw = replace[info.filename](raw)
            zout.writestr(info.filename, raw)
        for name, raw in (add or {}).items():
            zout.writestr(name, raw)
        if dup:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for name, raw in dup.items():
                    zout.writestr(name, raw)
    return out.getvalue()


def sub(old, new):
    return lambda b: b.replace(old, new)


def has(findings, text):
    return any(text in f for f in findings)


class CleanTests(unittest.TestCase):
    def test_clean_passes(self):
        self.assertEqual(scan_xlsx_bytes(clean_workbook_bytes()), [])

    def test_clean_without_chart_or_link(self):
        self.assertEqual(scan_xlsx_bytes(build(chart=False, link=False)), [])

    def test_hyperlink_rel_type_is_hyperlink(self):
        z = zipfile.ZipFile(io.BytesIO(clean_workbook_bytes()))
        rels = z.read("xl/worksheets/_rels/sheet1.xml.rels").decode()
        self.assertIn('/hyperlink"', rels)
        self.assertIn('TargetMode="External"', rels)

    def test_scan_or_raise_clean(self):
        self.assertIsNone(scan_or_raise(clean_workbook_bytes()))

    def test_part_names_sorted(self):
        names = part_names(clean_workbook_bytes())
        self.assertEqual(names, sorted(names))
        self.assertIn("xl/workbook.xml", names)

    def test_allowlist_is_anchored_tuple(self):
        self.assertIsInstance(PART_ALLOWLIST, tuple)
        self.assertGreaterEqual(len(PART_ALLOWLIST), 14)

    def test_deterministic(self):
        d = mutate(clean_workbook_bytes(), add={"xl/vbaProject.bin": b"x"})
        self.assertEqual(scan_xlsx_bytes(d), scan_xlsx_bytes(d))


class MutationTests(unittest.TestCase):
    def setUp(self):
        self.clean = clean_workbook_bytes()

    def assertFails(self, data, text=None):
        findings = scan_xlsx_bytes(data)
        self.assertTrue(findings, "expected findings")
        if text:
            self.assertTrue(has(findings, text), findings)
        with self.assertRaises(ScanError) as cm:
            scan_or_raise(data)
        self.assertTrue(cm.exception.findings)

    def test_not_a_zip(self):
        self.assertTrue(scan_xlsx_bytes(b"not a zip"))

    def test_vba_part_and_content_type(self):
        ct = sub(b"</Types>",
                 b'<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/></Types>')
        d = mutate(self.clean, add={"xl/vbaProject.bin": b"\x00"},
                   replace={"[Content_Types].xml": ct})
        self.assertFails(d, "vbaProject")

    def test_vba_part_alone(self):
        self.assertFails(mutate(self.clean, add={"xl/vbaProject.bin": b"\x00"}), "part")

    def test_macro_enabled_main_type(self):
        d = mutate(self.clean, replace={"[Content_Types].xml": sub(
            b"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
            b"application/vnd.ms-excel.sheet.macroEnabled.main+xml")})
        self.assertFails(d, "content")

    def test_macrosheet_type(self):
        d = mutate(self.clean, replace={"[Content_Types].xml": sub(
            b"</Types>", b'<Override PartName="/xl/m.xml" ContentType="application/vnd.ms-excel.macrosheet+xml"/></Types>')})
        self.assertFails(d, "content")

    def test_external_link_part(self):
        self.assertFails(mutate(self.clean, add={"xl/externalLinks/externalLink1.xml": b"<x/>"}), "part")

    def test_external_link_content_type(self):
        d = mutate(self.clean, replace={"[Content_Types].xml": sub(
            b"</Types>", b'<Override PartName="/xl/externalLinks/externalLink1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.externalLink+xml"/></Types>')})
        self.assertFails(d, "content")

    def test_external_relationship(self):
        rel = (b'<Relationship Id="rId99" Type="http://schemas.openxmlformats.org/'
               b'officeDocument/2006/relationships/externalLink" Target="file:///x.xlsx" '
               b'TargetMode="External"/></Relationships>')
        d = mutate(self.clean, replace={"xl/_rels/workbook.xml.rels": sub(b"</Relationships>", rel)})
        self.assertFails(d, "external")

    def test_internal_vba_relationship(self):
        rel = (b'<Relationship Id="rId98" Type="http://schemas.microsoft.com/office/'
               b'2006/relationships/vbaProject" Target="vbaProject.bin"/></Relationships>')
        d = mutate(self.clean, replace={"xl/_rels/workbook.xml.rels": sub(b"</Relationships>", rel)})
        self.assertFails(d, "relationship")

    def test_connections_part(self):
        self.assertFails(mutate(self.clean, add={"xl/connections.xml": b"<x/>"}), "part")

    def test_traversal_name(self):
        self.assertFails(mutate(self.clean, add={"xl/../evil.xml": b"<x/>"}), "name")

    def test_absolute_name(self):
        self.assertFails(mutate(self.clean, add={"/abs.xml": b"<x/>"}), "name")

    def test_duplicate_name(self):
        self.assertFails(mutate(self.clean, dup={"xl/styles.xml": b"<styleSheet/>"}), "duplicate")

    def test_doctype(self):
        d = mutate(self.clean, replace={"xl/styles.xml": lambda b: b"<!DOCTYPE x [<!ENTITY a 'b'>]>" + b})
        self.assertFails(d, "DOCTYPE")

    def test_hidden_sheet(self):
        d = mutate(self.clean, replace={"xl/workbook.xml": sub(b'<sheet name=', b'<sheet state="hidden" name=')})
        self.assertFails(d, "hidden")

    def test_very_hidden_sheet(self):
        d = mutate(self.clean, replace={"xl/workbook.xml": sub(b'<sheet name=', b'<sheet state="veryHidden" name=')})
        self.assertFails(d, "hidden")

    def test_external_references_element(self):
        d = mutate(self.clean, replace={"xl/workbook.xml": sub(
            b"</workbook>", b'<externalReferences><externalReference r:id="rId9"/></externalReferences></workbook>')})
        self.assertFails(d, "externalReferences")

    def test_defined_name_with_bracket(self):
        d = mutate(self.clean, replace={"xl/workbook.xml": sub(
            b"</workbook>", b'<definedNames><definedName name="X">[1]Sheet1!A1</definedName></definedNames></workbook>')})
        self.assertFails(d, "definedName")

    def test_ole_objects_in_sheet(self):
        d = mutate(self.clean, replace={"xl/worksheets/sheet1.xml": sub(
            b"</worksheet>", b"<oleObjects/></worksheet>")})
        self.assertFails(d, "oleObjects")


class FormulaBypassTests(unittest.TestCase):
    def check(self, formula, text=None, value=0):
        d = build(lambda wb, ws: ws.write_formula("D1", formula, None, value), chart=False)
        findings = scan_xlsx_bytes(d)
        self.assertTrue(findings, formula)
        if text:
            self.assertTrue(has(findings, text), findings)

    def test_external_workbook(self):
        self.check("=[ext.xlsx]Sheet1!A1", "formula")

    def test_dde(self):
        self.check("=cmd|' /C calc'!A0", "formula")

    def test_offset(self):
        self.check("=OFFSET(A1,1,0)", "OFFSET")

    def test_indirect_with_prefix(self):
        self.check("=_xlfn.XLOOKUP(A1,A1:A2,A1:A2)", "XLOOKUP")

    def test_url_in_formula(self):
        self.check('=A1&"http://x"', "formula")

    def test_unc(self):
        self.check("=\\\\host\\share\\a", "formula")

    def test_cached_string_result(self):
        self.check("=A1", "string", value="=1+1")

    def test_clean_formula_ok(self):
        d = build(lambda wb, ws: ws.write_formula("D1", "=SUM(A1:A2)", None, 3), chart=False)
        self.assertEqual(scan_xlsx_bytes(d), [])


class NonCellFormulaTests(unittest.TestCase):
    """CR-01: formulas outside worksheet <f> elements are scanned too."""

    def test_defined_name_dde(self):
        d = build(lambda wb, ws: wb.define_name("Evil", "=cmd|' /C calc'!A0"),
                  chart=False)
        self.assertTrue(has(scan_xlsx_bytes(d), "DDE"))

    def test_defined_name_banned_function(self):
        d = build(lambda wb, ws: wb.define_name("Evil", '=WEBSERVICE("x")'),
                  chart=False)
        self.assertTrue(has(scan_xlsx_bytes(d), "WEBSERVICE"))

    def test_data_validation_formula(self):
        d = build(lambda wb, ws: ws.data_validation("D1", {
            "validate": "custom", "value": '=WEBSERVICE("x")'}), chart=False)
        self.assertTrue(has(scan_xlsx_bytes(d), "WEBSERVICE"))

    def test_conditional_format_formula(self):
        d = build(lambda wb, ws: ws.conditional_format("A1:A2", {
            "type": "formula", "criteria": '=INDIRECT("A1")>0',
            "format": wb.add_format({"bold": True})}), chart=False)
        self.assertTrue(has(scan_xlsx_bytes(d), "INDIRECT"))

    def test_chart_formula(self):
        def fn(wb, ws):
            ch = wb.add_chart({"type": "line"})
            ch.add_series({"values": "=Sheet1!$A$1:$A$2"})
            ch.set_title({"name": "=cmd|' /C calc'!A0"})
            ws.insert_chart("E2", ch)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # XlsxWriter: unknown sheet 'cmd|..'
            d = build(fn, chart=False)
        self.assertTrue(has(scan_xlsx_bytes(d), "DDE"))

    def test_clean_non_cell_formulas_pass(self):
        def fn(wb, ws):
            wb.define_name("Ok_Name", "=Sheet1!$A$1")
            ws.data_validation("D1", {"validate": "list",
                                      "source": ["Low", "High"]})
            ws.conditional_format("A1:A2", {
                "type": "cell", "criteria": "==", "value": '"OK"',
                "format": wb.add_format({"bold": True})})
        self.assertEqual(scan_xlsx_bytes(build(fn)), [])


class StringBypassTests(unittest.TestCase):
    def test_injection_strings(self):
        for s in ("=1+1", "+1", "-1", "@SUM(A1)", "\tX", "\rX", "  =1"):
            with self.subTest(s=s):
                d = build(lambda wb, ws, s=s: ws.write_string("D1", s), chart=False)
                self.assertTrue(has(scan_xlsx_bytes(d), "string"))

    def test_control_characters(self):
        # WR-10: the byte gate enforces the same rule as CellWriter.text.
        for fn in (lambda wb, ws: ws.merge_range(3, 0, 3, 1, "a\x07b"),
                   lambda wb, ws: ws.write_string("D1", "a\x01b"),
                   lambda wb, ws: ws.write_string("D1", "a\x7fb"),
                   lambda wb, ws: ws.write_string("D1", "a\rb")):
            with self.subTest(fn=fn):
                d = build(fn, chart=False)
                self.assertTrue(has(scan_xlsx_bytes(d), "control character"))
        d = build(lambda wb, ws: ws.write_string("D1", "line1\nline2"), chart=False)
        self.assertEqual(scan_xlsx_bytes(d), [])

    def test_en_dash_ok(self):
        d = build(lambda wb, ws: ws.write_string("D1", "– ok"), chart=False)
        self.assertEqual(scan_xlsx_bytes(d), [])

    def test_inline_string(self):
        d = mutate(build(chart=False), replace={"xl/worksheets/sheet1.xml": sub(
            b"</sheetData>", b'<row r="9"><c r="A9" t="inlineStr"><is><t>=evil</t></is></c></row></sheetData>')})
        self.assertTrue(has(scan_xlsx_bytes(d), "string"))


class UrlBypassTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("https://evil.example/", "https://ec.europa.eu@evil.example/",
                    "https://eurostat.evil.com/", "http://ec.europa.eu/"):
            with self.subTest(url=url):
                d = build(lambda wb, ws, url=url: ws.write_url("D1", url), chart=False)
                self.assertTrue(has(scan_xlsx_bytes(d), "hyperlink"), url)

    def test_good_url_subdomain(self):
        d = build(lambda wb, ws: ws.write_url("D1", "https://re.jrc.ec.europa.eu/x"), chart=False)
        self.assertEqual(scan_xlsx_bytes(d), [])


class InternalLocationTests(unittest.TestCase):
    def test_internal_ok(self):
        d = build(lambda wb, ws: ws.write_url("D1", "internal:Sheet1!A1"), chart=False)
        self.assertEqual(scan_xlsx_bytes(d), [])

    def test_bad_locations(self):
        for loc in ("[1]Sheet1!A1", "file:x", "a://b", "a\\b"):
            with self.subTest(loc=loc):
                d = build(lambda wb, ws: ws.write_url("D1", "internal:Sheet1!A1"), chart=False)
                d = mutate(d, replace={"xl/worksheets/sheet1.xml": sub(
                    b'location="Sheet1!A1"', ('location="%s"' % loc).encode())})
                self.assertTrue(has(scan_xlsx_bytes(d), "hyperlink location"), loc)


if __name__ == "__main__":
    unittest.main()
