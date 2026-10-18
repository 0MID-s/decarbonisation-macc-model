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

    def test_numeric_text(self):
        # WR-06: Excel coerces numeric text in arithmetic.
        for f in ['=B1*"0.5"', '=B1*VALUE("12")', '=B1*" 12 "', '=B1*"5%"',
                  '=B1*"1,000"', '=B1*NUMBERVALUE("3")', '=B1*VALUE("1"&"1")',
                  '=B1*("1"&"1")', '=B1*"1E3"']:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f), f)
        for f in ['=IF(A1>0,"100 kg",1)', '=TEXT(A1,"0.0%")', '=TEXT(A1,"0")',
                  '=IFERROR(A1,"n/a")', '="Scenario: "&A1', '=IF(A1,"inf","nan")',
                  '=IF(A1,"",B1)', '=VALUE(A1)']:
            with self.subTest(f=f):
                self.assertEqual(lint_formula(f), [], f)

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

    def test_nested_mixes(self):
        # CR-02: aggregation hidden inside a selector, however deep.
        tags = make_tags()
        for f in ["=CHOOSE(1,SUM(F20,F21))", "=INDEX(SUMPRODUCT(F20,F21),1)",
                  "=CHOOSE(Idx,F20,F21)+F21", "=IF(A1,F20+F21,0)",
                  "=IF(A1,F20,F21)*F21", "=CHOOSE(Idx,(F20*F21),F20)",
                  "=IF(A1,CHOOSE(Idx,F20,MAX(F20:F21)),F21)",
                  "=CHOOSE(Idx,F20:F21,F20)", "=F20:F21", "=SUM(Row_LB,Row_MB)",
                  "=IF(F20>F21,Const_None,0)", "=ROUND(INDEX(F20:F21,Idx)+F21,0)",
                  "=INDEX((F20,F21),Idx)", "=CHOOSE(Idx,F20 F21,F20)"]:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f, "Calc", tags), f)

    def test_sheet_on_both_ends(self):
        # Excel accepts Calc!F20:Calc!F21; it must resolve, and a span
        # across two sheets must fail closed rather than pass untagged.
        tags = make_tags()
        for f in ["=SUM(Calc!F20:Calc!F21)", "=SUM('Calc'!F20:'Calc'!F21)",
                  "=SUM(Calc!F20:Other!F21)"]:
            with self.subTest(f=f):
                self.assertTrue(lint_formula(f, "Other", tags), f)
        self.assertEqual(lint_formula("=SUM(Calc!F20:Calc!AI20)", "Other", tags), [])

    def test_selection_passes(self):
        tags = make_tags()
        for f in ["=CHOOSE(Idx_Basis,F20,F21)", "=INDEX(F20:F21,Idx_Basis)",
                  "=IF(Basis_Sel=Const_None,F20,F21)",
                  "=IF(Basis_Sel=Const_None,Row_LB,Row_MB)",
                  "=CHOOSE(Idx,F20,F21)*Const_None",
                  "=IF(A1,F20,F21)*Rate_Disc", "=IFERROR(F20,F21)",
                  "=ROUND(CHOOSE(Idx,F20*Const_None,F21*Const_None),0)",
                  "=IF(A1,CHOOSE(Idx,F20,F21),F21)",
                  "=SUM(CHOOSE(Idx,F20,F21),G5)", "=F20*F20+G9"]:
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
