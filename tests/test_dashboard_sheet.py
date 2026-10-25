"""Dashboard tests (plan 05-04). Task 1: lint pre-tests for the non-link
formulas the Dashboard and Checks sheets use."""
import unittest

import build
from qa.lint import lint_formula

# Recorded outcome (Task 1): the OR of two comparisons against LB- and
# MB-tagged names is ACCEPTED by the lint (pinned below).
OR_FORMULA = "=OR(Dash_AbatedSel=M_Total_tLB,Dash_AbatedSel=M_Total_tMB)"


class LintPreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        holder = []
        ds = build.load_dataset("config")
        build.build_bytes("main", ds,
                          extra_builders=[lambda wb, s, c: holder.append(c)])
        cls.tags = holder[0].tags

    def ok(self, f):
        self.assertEqual(lint_formula(f, "Dashboard", self.tags), [], f)

    def test_choose_selected_basis(self):
        self.ok("=CHOOSE(M_BasisIdx,M_Total_tLB,M_Total_tMB)")
        self.ok("=CHOOSE(M_BasisIdx,BL_S12_LB,BL_S12_MB)")

    def test_share_and_tile_vs_macc(self):
        self.ok("=Dash_AbatedSel/Dash_S12Sel")
        self.ok("=ABS(Dash_AbatedSel-MACC_TotalAbatement)<="
                "COUNT(MACC_Chart_Width)*Const_MACCRoundTol")

    def test_single_comparisons_pass(self):
        self.ok("=IFERROR(Dash_AbatedSel=M_Total_tLB,FALSE)")
        self.ok("=IFERROR(Dash_AbatedSel=M_Total_tMB,FALSE)")

    def test_or_formula_outcome_recorded(self):
        problems = lint_formula(OR_FORMULA, "Checks", self.tags)
        # Pinned: ACCEPTED, because Dash_AbatedSel is an untagged helper and
        # each operand of the OR is a single comparison with one tagged name.
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
