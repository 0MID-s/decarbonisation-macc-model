"""Tests for the allowlisted raw-data fetcher (SET-04, T-01-21). No network."""
import hashlib
import io
import json
import os
import socket
import stat
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from tools import fetch_raw
from tools.fetch_raw import MAX_BYTES, FetchError, fetch, plan_target

GOOD = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_pc_205"


class FakeResp(io.BytesIO):
    def __init__(self, data, url=GOOD):
        super().__init__(data)
        self._url = url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        p = mock.patch("socket.create_connection", side_effect=AssertionError("network used"))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)


class PlanTargetTests(Base):
    def test_accepts_good(self):
        p = plan_target(GOOD, "Src_Eurostat", self.root, name="nrg_pc_205.json")
        self.assertEqual(p, self.root.resolve() / "Src_Eurostat" / "nrg_pc_205.json")

    def test_filename_from_url(self):
        p = plan_target("https://www.gov.uk/files/factors.csv", "Src_Gov", self.root)
        self.assertEqual(p.name, "factors.csv")

    def test_rejects_urls(self):
        for url in ("http://ec.europa.eu/a.csv", "https://evil.com/a.csv",
                    "https://ec.europa.eu@evil.com/a.csv", "https://eurostat.evil.com/a.csv"):
            with self.subTest(url=url):
                with self.assertRaises(FetchError):
                    plan_target(url, "Src_X", self.root)

    def test_rejects_forbidden_suffix(self):
        for n in ("a.xlsm", "a.exe", "a.zip", "a.XLSM", "a.py", "a.xls",
                  # CR-03: denylist gaps, now closed by the allowlist
                  "x.xltm", "x.xlam", "x.docm", "x.scr", "x.hta", "x.command",
                  "x.7z", "x.tar.gz", "x.xlsm.", "x.csv.", "x.csv ", "noext"):
            with self.subTest(n=n):
                with self.assertRaises(FetchError):
                    plan_target(GOOD, "Src_X", self.root, name=n)

    def test_allowed_suffixes(self):
        for n in ("a.xlsx", "a.csv", "a.json", "a.tsv", "a.pdf", "a.xml"):
            with self.subTest(n=n):
                plan_target(GOOD, "Src_X", self.root, name=n)

    def test_rejects_manifest_name(self):
        for n in ("MANIFEST.jsonl", "manifest.JSONL"):
            with self.subTest(n=n):
                with self.assertRaises(FetchError):
                    plan_target(GOOD, "Src_X", self.root, name=n)
        with self.assertRaises(FetchError):
            plan_target("https://ec.europa.eu/x/MANIFEST.jsonl", "Src_X", self.root)

    def test_refuses_overwrite(self):
        d = self.root / "Src_X"
        d.mkdir()
        (d / "a.csv").write_bytes(b"old")
        with self.assertRaises(FetchError):
            plan_target(GOOD, "Src_X", self.root, name="a.csv")

    def test_rejects_traversal_names(self):
        for n in ("../a.csv", "a/b.csv", "..", "a\\b.csv", "/etc/a.csv"):
            with self.subTest(n=n):
                with self.assertRaises(FetchError):
                    plan_target(GOOD, "Src_X", self.root, name=n)

    def test_rejects_bad_source_ids(self):
        for sid in ("src_x", "../Src_X", "Src", "Src_X/..", "", "Src X"):
            with self.subTest(sid=sid):
                with self.assertRaises(FetchError):
                    plan_target(GOOD, sid, self.root, name="a.csv")

    def test_no_name_no_basename_refused(self):
        with self.assertRaises(FetchError):
            plan_target("https://ec.europa.eu/", "Src_X", self.root)


class FetchTests(Base):
    def run_fetch(self, data, name="d.json", **kw):
        with mock.patch.object(urllib.request.OpenerDirector, "open",
                               return_value=FakeResp(data, kw.pop("final", GOOD))):
            return fetch(GOOD, "Src_X", self.root, name=name, **kw)

    def test_success_writes_file_and_manifest(self):
        data = b'{"a": 1}'
        p = self.run_fetch(data)
        self.assertEqual(p.read_bytes(), data)
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o644)
        lines = (self.root / "Src_X" / "MANIFEST.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(rec["bytes"], len(data))
        self.assertEqual(rec["file"], "d.json")
        self.assertEqual(rec["source_id"], "Src_X")
        self.assertEqual(rec["url"], GOOD)
        for k in ("final_url", "retrieved_utc"):
            self.assertIn(k, rec)

    def test_manifest_appends(self):
        self.run_fetch(b"1", name="a.json")
        self.run_fetch(b"2", name="b.json")
        lines = (self.root / "Src_X" / "MANIFEST.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 2)

    def test_refetch_same_name_refused(self):
        # CR-03: an earlier manifest sha256 must keep matching the file on disk.
        self.run_fetch(b"1")
        with self.assertRaises(FetchError):
            self.run_fetch(b"2")
        self.assertEqual((self.root / "Src_X" / "d.json").read_bytes(), b"1")
        lines = (self.root / "Src_X" / "MANIFEST.jsonl").read_text().splitlines()
        self.assertEqual(len(lines), 1)

    def test_oversize_aborts_no_file(self):
        with mock.patch.object(fetch_raw, "MAX_BYTES", 10):
            with self.assertRaises(FetchError):
                self.run_fetch(b"x" * 100)
        d = self.root / "Src_X"
        self.assertEqual([f for f in d.iterdir()] if d.exists() else [], [])

    def test_max_bytes_constant(self):
        self.assertEqual(MAX_BYTES, 50 * 1024 * 1024)

    def test_final_url_off_allowlist_refused(self):
        with self.assertRaises(FetchError):
            self.run_fetch(b"x", final="https://evil.com/a")
        d = self.root / "Src_X"
        self.assertEqual([f for f in d.iterdir()] if d.exists() else [], [])

    def test_redirect_handler_refuses_off_allowlist(self):
        h = fetch_raw.AllowlistRedirectHandler()
        req = urllib.request.Request(GOOD)
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(req, None, 302, "Found", {}, "https://evil.com/x")
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(req, None, 302, "Found", {}, "http://ec.europa.eu/x")

    def test_redirect_handler_allows_allowlisted(self):
        h = fetch_raw.AllowlistRedirectHandler()
        req = urllib.request.Request(GOOD)
        new = h.redirect_request(req, io.BytesIO(), 302, "Found", {}, "https://www.gov.uk/x")
        self.assertIsNotNone(new)

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as cm:
            fetch_raw.main(["--help"])
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
