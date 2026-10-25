"""Quote-check for docs/MODEL_WALKTHROUGH.md (LEARN-02, D-21).

Every figure quoted in the walkthrough sits in the "Figures quoted" table as
Name | Value as written | Rule. Each is recomputed from the default-state
build (evaluate_names) and must equal the written string. Outside the table
and fenced code, any money/percent figure, decimal number or number of four
or more digits that is not listed fails the scan.
"""
import os
import re
import unittest

DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "MODEL_WALKTHROUGH.md")
RULES = ("eur0", "t0", "t1", "pct1", "int")


def parse_figures(text):
    """Return [(name, written, rule)] from the table under '## Figures quoted'."""
    m = re.search(r"^## Figures quoted\s*$", text, re.M)
    if not m:
        return []
    rows = []
    for line in text[m.end():].splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if rows and line.startswith("#"):
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[2] not in RULES:
            continue
        name = cells[0].strip("`")
        rows.append((name, cells[1].strip("`"), cells[2]))
    return rows


def format_value(x, rule):
    if rule == "eur0":
        v = int(round(x))
        return ("-" if v < 0 else "") + "EUR {:,}".format(abs(v))
    if rule == "t0":
        return "{:,} tCO2e".format(int(round(x)))
    if rule == "t1":
        return "{:,.1f}".format(x)
    if rule == "pct1":
        return "{:.1f}%".format(x * 100)
    if rule == "int":
        return str(int(round(x)))
    raise ValueError(rule)


_NUM = r"-?\d(?:,\d{3}|\d)*(?:\.\d+)?"
_TOKEN = re.compile(
    r"(?:-?EUR\s*" + _NUM + r"|-?€\s*" + _NUM + r"|" + _NUM + r"\s*%|" + _NUM + r"(?:\s*tCO2e)?)")
_REFS = re.compile(r"\b(?:E1-\d+|S2-\d+|\d+\([a-z]\)(?:\([ivx]+\))?|v\d+(?:\.\d+)+|\d+\.\d+\.\d+)")


def _strip_nonprose(text):
    m = re.search(r"^## Figures quoted\s*$", text, re.M)
    if m:
        text = text[:m.start()]
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)          # inline code (names, cells)
    text = re.sub(r"\]\([^)]*\)", "]", text)      # link targets
    text = _REFS.sub(" ", text)
    return text


def stray_numbers(text, written=None):
    """Tokens in prose that are quoted figures but not listed."""
    if written is None:
        written = set(w for _, w, _ in parse_figures(text))
    prose = _strip_nonprose(text)
    bad = []
    for m in _TOKEN.finditer(prose):
        tok = m.group(0).strip()
        if m.start() > 0 and prose[m.start() - 1].isalpha():
            continue  # part of a word or id such as ESRS2 or M_LED
        digits = re.sub(r"\D", "", tok)
        core = re.sub(r"(?i)tco2e|eur|€|%", "", tok).strip().lstrip("-").strip()
        has_unit = "EUR" in tok or "€" in tok or "%" in tok
        if tok in written or tok.replace(" ", " ") in written:
            continue
        # also accept the bare number of a listed value
        if any(core == re.sub(r"(?i)tco2e|eur|€|%", "", w).strip().lstrip("-").strip()
               for w in written):
            continue
        if has_unit:
            bad.append(tok)
            continue
        if "." in core:
            bad.append(tok)
            continue
        if len(digits) >= 4:
            if re.fullmatch(r"20\d\d|2100", core):
                continue  # years 2000 to 2100
            bad.append(tok)
            continue
        # integers below 100 are allowed
    return bad


class ParserTests(unittest.TestCase):
    TEXT = (
        "Intro 12 states, year 2030 and E1-7 are fine.\n\n"
        "## Figures quoted\n\n"
        "| Name | Value as written | Rule |\n|---|---|---|\n"
        "| `M_X_NPV` | -EUR 1,234 | eur0 |\n"
        "| `Dash_Share` | 12.3% | pct1 |\n"
        "| `MACC_TotalAbatement` | 5,000 tCO2e | t0 |\n")

    def test_parse(self):
        rows = parse_figures(self.TEXT)
        self.assertEqual(rows, [("M_X_NPV", "-EUR 1,234", "eur0"),
                                ("Dash_Share", "12.3%", "pct1"),
                                ("MACC_TotalAbatement", "5,000 tCO2e", "t0")])

    def test_format(self):
        self.assertEqual(format_value(-1233.6, "eur0"), "-EUR 1,234")
        self.assertEqual(format_value(0.1234, "pct1"), "12.3%")
        self.assertEqual(format_value(4999.7, "t0"), "5,000 tCO2e")
        self.assertEqual(format_value(1234.56, "t1"), "1,234.6")
        self.assertEqual(format_value(12.0, "int"), "12")

    def test_stray_ok(self):
        self.assertEqual(stray_numbers(self.TEXT), [])

    def test_stray_caught(self):
        t = "We save EUR 9,999 and 45.5% and 12345 units.\n" + self.TEXT
        self.assertEqual(sorted(stray_numbers(t)),
                         sorted(["EUR 9,999", "45.5%", "12345"]))

    def test_listed_in_prose_ok(self):
        t = "The NPV is -EUR 1,234 today.\n" + self.TEXT
        self.assertEqual(stray_numbers(t), [])


@unittest.skipUnless(os.path.exists(DOC),
                     "docs/MODEL_WALKTHROUGH.md does not exist yet")
class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build
        from qa.formula_eval import evaluate_names
        with open(DOC, encoding="utf-8") as f:
            cls.text = f.read()
        cls.rows = parse_figures(cls.text)
        ds = build.load_dataset("config")
        data, _ = build.build_bytes("main", ds)
        names = sorted(set(n for n, _, _ in cls.rows))
        cls.values = evaluate_names(data, names) if names else {}

    def test_table_present(self):
        self.assertGreater(len(self.rows), 10)

    def test_every_row_matches_workbook(self):
        bad = []
        for name, written, rule in self.rows:
            v = self.values[name]
            if isinstance(v, list):
                bad.append((name, "range name"))
                continue
            got = format_value(v, rule)
            if got != written:
                bad.append((name, written, got))
        self.assertEqual(bad, [])

    def test_no_stray_numbers(self):
        bad = stray_numbers(self.text)
        self.assertEqual(bad, [], "unlisted figures: %s" % bad)

    def test_no_private_notes_reference(self):
        self.assertNotIn("Interview-Notes", self.text)


if __name__ == "__main__":
    unittest.main()
