"""Tests for tools/fetch_all.py. No network."""
import io
import re
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from config.schema import ID_PATTERN
from config.security import host_allowed
from tools import fetch_all
from tools.fetch_raw import ALLOWED_SUFFIXES


class FetchListTests(unittest.TestCase):
    def test_entries_valid(self):
        for sid, name, url in fetch_all.FETCHES:
            with self.subTest(name=name):
                self.assertTrue(host_allowed(url), url)
                self.assertTrue(name.lower().endswith(ALLOWED_SUFFIXES))
                self.assertTrue(re.match(ID_PATTERN, sid))

    def test_forbidden(self):
        for sid, name, url in fetch_all.FETCHES:
            path = urlsplit(url).path.lower()
            self.assertFalse(name.lower().endswith((".xls", ".zip")))
            self.assertFalse(path.endswith((".xls", ".zip")))
            for bad in ("eur-lex", "eex.com", "stern.nyu.edu", "iiasa.ac.at", "bls.gov"):
                self.assertNotIn(bad, url)

    def test_required_entries(self):
        self.assertTrue(any(s == "Src_EurostatFX" and "ert_bil_eur_a" in u
                            for s, n, u in fetch_all.FETCHES))
        self.assertTrue(any("nrg_bal=FC_IND_CPC_E" in u for s, n, u in fetch_all.FETCHES))
        self.assertTrue(any("sbs_sc_ovw" in u and "C20" in u and "C21" in u
                            for s, n, u in fetch_all.FETCHES))


class MainTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        for p in (mock.patch.object(fetch_all, "DEFAULT_ROOT", Path(self._tmp.name)),
                  mock.patch("socket.create_connection", side_effect=AssertionError("net"))):
            p.start()
            self.addCleanup(p.stop)

    def run_main(self, argv=()):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = fetch_all.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_fetches_all(self):
        with mock.patch.object(fetch_all, "fetch", return_value="ok") as f:
            rc, out, _ = self.run_main()
        self.assertEqual(rc, 0)
        self.assertEqual(f.call_count, len(fetch_all.FETCHES))

    def test_skips_existing(self):
        sid, name, _ = fetch_all.FETCHES[0]
        d = Path(self._tmp.name) / sid
        d.mkdir()
        (d / name).write_text("x")
        with mock.patch.object(fetch_all, "fetch", return_value="ok") as f:
            rc, out, _ = self.run_main()
        self.assertEqual(rc, 0)
        self.assertIn("skip", out)
        self.assertEqual(f.call_count, len(fetch_all.FETCHES) - 1)

    def test_failure_continues(self):
        with mock.patch.object(fetch_all, "fetch",
                               side_effect=urllib.error.URLError("boom")) as f:
            rc, _, err = self.run_main()
        self.assertEqual(rc, 1)
        self.assertEqual(f.call_count, len(fetch_all.FETCHES))
        self.assertIn("boom", err)

    def test_only(self):
        with mock.patch.object(fetch_all, "fetch", return_value="ok") as f:
            self.run_main(["--only", "Src_PVGIS"])
        self.assertEqual(f.call_count, 2)


if __name__ == "__main__":
    unittest.main()
