"""QA-02: in every selector state, every formula equals the reference.

The workbook is built (test-only) in each of the 2 bases x 3 scenarios with
cached values from checkmodel.measures_reference, then every formula cell on
every sheet is re-evaluated by the independent evaluator (D-27).
"""
import dataclasses
import hashlib
import unittest

import build
from checkmodel.measures_reference import (
    BASES, DEFAULT_STATE, SCENARIOS_UI, compute_measures)
from qa.formula_eval import compare_cached, evaluate_names


class SixStateQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = build.load_dataset("config")

    def test_bases_and_scenarios_cover_six_states(self):
        self.assertEqual(set(BASES), {"Location-based", "Market-based"})
        self.assertEqual(len(BASES) * len(SCENARIOS_UI), 6)

    def test_every_formula_equals_reference_in_each_state(self):
        for basis in BASES:
            for scen in SCENARIOS_UI:
                with self.subTest(state=(basis, scen)):
                    ds = dataclasses.replace(self.base,
                                             selector_state=(basis, scen))
                    data, _ = build.build_bytes("main", ds)
                    bad, n = compare_cached(data)
                    self.assertEqual(bad, [], (basis, scen, bad[:5]))
                    self.assertGreater(n, 1000)
                    ref = compute_measures(ds.inputs, basis, scen)
                    out = evaluate_names(data, ["M_Check_All", "M_RC_tLB"])
                    self.assertIs(out["M_Check_All"], True)
                    if basis == "Location-based":
                        self.assertTrue(all(x == 0 for x in out["M_RC_tLB"]))
                    self.assertEqual(ref.basis, basis)
                    self.assertEqual(ref.scenario, scen)

    def test_default_build_is_default_state_and_stable(self):
        self.assertEqual(build.selector_state(self.base), DEFAULT_STATE)
        d1, _ = build.build_bytes("main", self.base)
        d2, _ = build.build_bytes("main", dataclasses.replace(
            self.base, selector_state=DEFAULT_STATE))
        self.assertEqual(hashlib.sha256(d1).hexdigest(),
                         hashlib.sha256(d2).hexdigest())


if __name__ == "__main__":
    unittest.main()
