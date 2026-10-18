"""Tests for config.security helpers (D-13, D-15, T-01-06, T-01-07)."""
import unittest

from config.security import (
    ALLOWED_DOMAINS, BANNED_FUNCTIONS, host_allowed, is_injection_string,
)


class HostAllowedTests(unittest.TestCase):
    def test_allowed_hosts(self):
        for url in (
            "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_205",
            "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc",
            "https://www.gov.uk/x",
            "https://data.ecb.europa.eu/x",
            "https://data.ene.iiasa.ac.at/ngfs/",
        ):
            with self.subTest(url=url):
                self.assertTrue(host_allowed(url))

    def test_rejected_hosts(self):
        for url in (
            "http://ec.europa.eu/",
            "https://eurostat.evil.com/",
            "https://ec.europa.eu.evil.com/",
            "https://ec.europa.eu@evil.example/",
            "https://notgov.uk/",
            "ftp://gov.uk/",
            "https://xn--80ak6aa92e.com/",
        ):
            with self.subTest(url=url):
                self.assertFalse(host_allowed(url))

    def test_empty_and_non_ascii(self):
        self.assertFalse(host_allowed(""))
        self.assertFalse(host_allowed("https:///path"))
        self.assertFalse(host_allowed("https://gov.uké/"))

    def test_trailing_dot_normalised(self):
        self.assertTrue(host_allowed("https://www.gov.uk./x"))

    def test_allowed_domains_sorted_unique(self):
        self.assertEqual(list(ALLOWED_DOMAINS), sorted(set(ALLOWED_DOMAINS)))


class InjectionTests(unittest.TestCase):
    def test_injection_true(self):
        for s in ("=1+1", " =A1", "+1", "-1", "@SUM(A1)", "\tX", "\rX"):
            with self.subTest(s=s):
                self.assertTrue(is_injection_string(s))

    def test_injection_false(self):
        for s in ("Sourced", "– dash", "2026", "EUR/kWh"):
            with self.subTest(s=s):
                self.assertFalse(is_injection_string(s))


class BannedFunctionTests(unittest.TestCase):
    def test_contains_core(self):
        self.assertIn("OFFSET", BANNED_FUNCTIONS)
        self.assertIn("LET", BANNED_FUNCTIONS)
        self.assertIn("INDIRECT", BANNED_FUNCTIONS)


if __name__ == "__main__":
    unittest.main()
