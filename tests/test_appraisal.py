"""Hand-computed tests for the independent finance primitives (plan 03-05)."""
import unittest

from checkmodel import appraisal as ap


class Discounting(unittest.TestCase):
    def test_discount_factors(self):
        df = ap.discount_factors(0.1, 3)
        for got, want in zip(df, [1.0, 1 / 1.1, 1 / 1.21]):
            self.assertAlmostEqual(got, want, places=12)

    def test_npv0(self):
        self.assertAlmostEqual(ap.npv0(0.1, [-100, 110]), 0.0, places=10)
        cf = [-50, 20, 30, 40]
        self.assertAlmostEqual(ap.npv0(0.0, cf), sum(cf), places=12)

    def test_excel_npv(self):
        self.assertAlmostEqual(ap.excel_npv(0.1, [110, 121]), 200.0, places=9)
        cf = [-100, 30, 40, 50, 60]
        self.assertAlmostEqual(cf[0] + ap.excel_npv(0.07, cf[1:]),
                               ap.npv0(0.07, cf), places=9)


class Irr(unittest.TestCase):
    def test_sign_changes(self):
        self.assertEqual(ap.sign_changes([-100, 0, 50, -10, 60]), 3)

    def test_irr_simple(self):
        self.assertAlmostEqual(ap.irr([-100, 110]), 0.1, places=10)

    def test_irr_single_root_with_dip(self):
        cf = [-100, 60, 60, -10, 60]
        r = ap.irr(cf)
        self.assertIsNotNone(r)
        self.assertAlmostEqual(ap.npv0(r, cf), 0.0, places=6)

    def test_irr_two_roots_none(self):
        self.assertIsNone(ap.irr([-100, 230, -132]))

    def test_irr_no_root_none(self):
        self.assertIsNone(ap.irr([0, -5, -5]))
        self.assertIsNone(ap.irr([-100, -5, -5]))

    def test_irr_text(self):
        self.assertAlmostEqual(ap.irr_text([-100, 110]), 0.1, places=10)
        self.assertEqual(ap.irr_text([0, 10, 10]), "n/a (no upfront outlay)")
        self.assertEqual(ap.irr_text([-100, -5]), "n/a (never pays back)")
        self.assertEqual(ap.irr_text([-100, 230, -132]),
                         "n/a (no solution found)")

    def test_multiple_sign_flag(self):
        self.assertEqual(ap.multiple_sign_flag([-100, 230, -132]),
                         "multiple sign changes: IRR may not be unique")
        self.assertEqual(ap.multiple_sign_flag([-100, 110]), "")


class Payback(unittest.TestCase):
    def test_interpolated(self):
        self.assertAlmostEqual(ap.payback([-100, 30, 30, 30, 30, 30]),
                               3 + 10 / 30, places=12)

    def test_no_outlay(self):
        self.assertEqual(ap.payback([0, 10]), "n/a (no upfront outlay)")

    def test_never(self):
        self.assertEqual(ap.payback([-100, 10, 10]), "Not within 2055")

    def test_later_dip_ignored(self):
        self.assertAlmostEqual(ap.payback([-100, 120, -200, 10]),
                               0 + 100 / 120, places=12)

    def test_discounted(self):
        cf = [-100, 60, 60]
        df = ap.discount_factors(0.1, 3)
        want = ap.payback([c * d for c, d in zip(cf, df)])
        self.assertAlmostEqual(ap.discounted_payback(cf, 0.1), want, places=12)


class Levelised(unittest.TestCase):
    def test_levelised(self):
        self.assertAlmostEqual(ap.levelised(-500, 10), 50.0)
        self.assertEqual(ap.levelised(-500, 0),
                         "n/a (no abatement on this basis)")
        self.assertEqual(ap.break_even(-500, 10), ap.levelised(-500, 10))

    def test_crf(self):
        r, n = 0.05, 10
        self.assertAlmostEqual(ap.crf(r, n), r / (1 - 1 / (1 + r) ** n))
        self.assertAlmostEqual(ap.crf(0.0, 8), 1 / 8)

    def test_annuity_equals_levelised_for_flat_project(self):
        r, life, capex, benefit, tonnes = 0.06, 10, 1000.0, 50.0, 20.0
        cf = [-capex] + [benefit] * life
        df = ap.discount_factors(r, life + 1)
        npv = ap.npv0(r, cf)
        pv_t = sum(tonnes * d for d in df[1:])
        pv_b = sum(benefit * d for d in df[1:])
        self.assertAlmostEqual(ap.levelised(npv, pv_t),
                               ap.annuity_cost(r, life, capex, pv_b, pv_t),
                               places=9)

    def test_annuity_equals_levelised_for_any_profile(self):
        # WR-10: one CRF over the horizon annualises cost and tonnes, so the
        # identity holds for uneven benefits, tonnes, replacements and a
        # residual value, not only for flat profiles.
        r, ny, life, capex = 0.07, 30, 12, 5000.0
        repl = ap.replacement_flags(ny, life)
        res = ap.residual_fraction(ny - 1, life)
        ben = [0.0] + [300.0 * 0.97 ** n for n in range(1, ny)]
        t = [0.0] + [40.0 * 1.05 ** n for n in range(1, ny)]
        cf = [(-capex if n == 0 else 0.0) - capex * repl[n] + ben[n]
              + (capex * res if n == ny - 1 else 0.0) for n in range(ny)]
        df = ap.discount_factors(r, ny)
        pv_cap = capex * (1 + sum(d * f for d, f in zip(df, repl))
                          - res * df[-1])
        lev = ap.levelised(ap.npv0(r, cf), ap.npv0(r, t))
        ann = ap.annuity_cost(r, ny - 1, pv_cap, ap.npv0(r, ben),
                              ap.npv0(r, t))
        self.assertAlmostEqual(lev, ann, places=9)

    def test_levelised_price(self):
        p, d, o = [10.0, 20.0], [1.0, 0.5], [2.0, 4.0]
        want = (10 * 1 * 2 + 20 * 0.5 * 4) / (1 * 2 + 0.5 * 4)
        self.assertAlmostEqual(ap.levelised_price(p, d, o), want)


class Replacement(unittest.TestCase):
    def test_residual_fraction(self):
        self.assertAlmostEqual(ap.residual_fraction(29, 15), 1 / 15)
        self.assertAlmostEqual(ap.residual_fraction(29, 40), 11 / 40)
        self.assertAlmostEqual(ap.residual_fraction(29, 20), 11 / 20)
        self.assertAlmostEqual(ap.residual_fraction(29, 8), 3 / 8)
        self.assertEqual(ap.residual_fraction(30, 15), 0.0)

    def test_replacement_flags(self):
        def at(life):
            f = ap.replacement_flags(30, life)
            self.assertEqual(len(f), 30)
            return [n for n, v in enumerate(f) if v]
        self.assertEqual(at(8), [8, 16, 24])
        self.assertEqual(at(15), [15])
        self.assertEqual(at(40), [])


if __name__ == "__main__":
    unittest.main()
