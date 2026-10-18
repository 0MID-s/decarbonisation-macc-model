"""Deliberate bad-formula tests for the D-15 formula lint."""
import unittest

from qa.lint import LintError, RangeTagIndex, lint_formula, lint_or_raise


def make_tags():
    t = RangeTagIndex()
    t.add("Calc", 19, 5, 19, 34, "LB")   # F20:AI20
    t.add("Calc", 20, 5, 20, 34, "MB")   # F21:AI21
    t.add_name("Row_LB", "Calc", 19, 5, 19, 34)
    t.add_name("Row_MB", "Calc", 20, 5, 20, 34)
    return t


class LiteralRules(unittest.TestCase):
    def test_bad_literals(self):
        for f in ["=A1*1000", "=A1*3.6", "=A1*8760", "=A1*12", "=A1*1E3",
                  "=IF(A1>0.5,1,0)", "=A1*5%", "=SUM({1,2})", "=A1*1E-3"]:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f), f)

    def test_inf_name_pinned(self):
        # Tokenizer reads Inf as a NUMBER; the lint flags it (pinned).
        self.assertTrue(lint_formula("=A1*Inf"))


class BannedFunctions(unittest.TestCase):
    def test_banned(self):
        for f in ["=OFFSET(A1,1,0)", '=INDIRECT("A1")', "=LAMBDA(x,x)(1)",
                  "=LET(x,1,x)", "=XLOOKUP(1,A:A,B:B)",
                  "=_xlfn.XLOOKUP(1,A:A,B:B)", "=FILTER(A1:A5,B1:B5)",
                  "=SORT(A1:A5)", "=NOW()", "=TODAY()", "=RAND()",
                  "=RANDBETWEEN(0,1)", '=WEBSERVICE("x")',
                  '=HYPERLINK("https://evil.example","x")']:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f), f)


class ReferenceAndInjection(unittest.TestCase):
    def test_external_and_spill(self):
        for f in ["=[ext.xlsx]Sheet1!A1", "=A1#", "=cmd|' /C calc'!A0"]:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f), f)

    def test_text_url_and_unc(self):
        self.assertTrue(lint_formula('="http://x"'))
        self.assertTrue(lint_formula('="file:x"'))
        self.assertTrue(lint_formula('="\\\\\\\\host\\\\share"'))

    def test_no_leading_equals(self):
        self.assertTrue(lint_formula("A1+B1"))

    def test_lint_or_raise(self):
        with self.assertRaises(LintError) as cm:
            lint_or_raise("=A1*1000")
        self.assertTrue(cm.exception.problems)
        lint_or_raise("=A1*Rate_Disc")


class LbMb(unittest.TestCase):
    def test_bad_mixes(self):
        tags = make_tags()
        for f in ["=F20+F21", "=F20-F21", "=SUM(F20:F21)", "=SUM(F20,F21)",
                  "=Row_LB+Row_MB", "=CHOOSE(Idx,F20,F21)+F21"]:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f, "Calc", tags), f)

    def test_selection_passes(self):
        tags = make_tags()
        for f in ["=CHOOSE(Idx_Basis,F20,F21)", "=INDEX(F20:F21,Idx_Basis)"]:
            with self.subTest(f=f):
                self.assertEqual(lint_formula(f, "Calc", tags), [], f)

    def test_other_sheet_not_confused(self):
        tags = make_tags()
        self.assertEqual(lint_formula("=F20+F21", "Other", tags), [])
        self.assertTrue(lint_formula("=Calc!F20+Calc!F21", "Other", tags))


class GoodPatterns(unittest.TestCase):
    def test_good(self):
        for f in ["=NPV(Rate_Disc,F5:AI5)", "=INDEX(r,MATCH(x,l,0))",
                  "=1/(1+Rate_Disc)^(F$5-Year_Base)",
                  '=IFERROR(IRR(F5:AI5),"n/a")', '=TEXT(A1,"0.0%")',
                  "=A1*-1", "=ROUND(A1,0)", "=CHOOSE(Idx_Basis,F20,F21)",
                  "=INDEX(F20:F21,Idx_Basis)", "=F20*Rate_Disc",
                  "='Q3 2026'!A1*B1", '="Scenario: "&Sel_Scenario',
                  "=D12*F12", '=IF(A1>0,"100 kg",1)']:
            with self.subTest(f=f):
                self.assertEqual(lint_formula(f), [], f)


class TagIndex(unittest.TestCase):
    def test_parsing(self):
        t = make_tags()
        self.assertEqual(t.tags_for("F20", "Calc"), frozenset(["LB"]))
        self.assertEqual(t.tags_for("$F$21", "Calc"), frozenset(["MB"]))
        self.assertEqual(t.tags_for("F20:F21", "Calc"), frozenset(["LB", "MB"]))
        self.assertEqual(t.tags_for("Calc!F20", "X"), frozenset(["LB"]))
        self.assertEqual(t.tags_for("Row_MB", "X"), frozenset(["MB"]))
        self.assertEqual(t.tags_for("Nope", "X"), frozenset())
        t.add("Q3 x", 0, 0, 0, 0, "LB")
        self.assertEqual(t.tags_for("'Q3 x'!$A$1", "X"), frozenset(["LB"]))
        self.assertEqual(t.tags_for("20:20", "Calc"), frozenset(["LB"]))
        self.assertEqual(t.tags_for("F:F", "Calc"), frozenset(["LB", "MB"]))


if __name__ == "__main__":
    unittest.main()
