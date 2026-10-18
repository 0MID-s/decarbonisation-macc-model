"""Allowlisted, size-capped, manifest-recording downloader for data_raw/.

SET-04 / T-01-21. Only https URLs on official hosts (config.security) are
fetched, into their own data_raw/<source_id>/ directory. Downloaded bytes are
only ever written to disk (mode 0644) and hashed: never executed, extracted or
parsed here. Real downloads are Phase 2 work.

CLI: python3 -I tools/fetch_raw.py --source-id Src_X --url https://... [--name f.csv]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:  # needed under `python -I`
    sys.path.insert(0, str(_ROOT))

from config.schema import ID_PATTERN  # noqa: E402
from config.security import host_allowed  # noqa: E402

MAX_BYTES = 50 * 1024 * 1024
TIMEOUT_S = 60  # per blocking socket operation
TOTAL_TIMEOUT_S = 300  # whole download (WR-11)
CHUNK = 64 * 1024
# Allowlist, not denylist (CR-03): data formats only. Macro-capable Office
# files (.xlsm, .xltm, .xlam, .docm, legacy .xls), executables, scripts and
# archives are never stored. Legacy .xls (e.g. Damodaran) is deliberately not
# on the list; adding it would be a reviewed, documented exception.
ALLOWED_SUFFIXES = (".csv", ".tsv", ".json", ".xlsx", ".pdf", ".txt", ".xml")
MANIFEST_NAME = "MANIFEST.jsonl"
DEFAULT_ROOT = _ROOT / "data_raw"


class FetchError(RuntimeError):
    pass


class AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-checks the host allowlist (https only) on every redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not host_allowed(newurl):
            raise urllib.error.URLError("redirect to non-allowlisted URL refused: %s" % newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def plan_target(url, source_id, root, name=None):
    if not host_allowed(url):
        raise FetchError("URL is not https on an allowlisted official host: %s" % url)
    if not re.match(ID_PATTERN, source_id or ""):
        raise FetchError("invalid source id: %r" % source_id)
    if name is None:
        name = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
        if not name:
            raise FetchError("cannot derive a file name from the URL; pass --name")
    if (name in ("", ".", "..") or "/" in name or "\\" in name or ".." in name
            or "\x00" in name or name.startswith(".")):
        raise FetchError("unsafe file name: %r" % name)
    if name.rstrip(" .") != name or not name.lower().endswith(ALLOWED_SUFFIXES):
        raise FetchError("file type not on allowlist: %s" % name)
    if name.upper() == MANIFEST_NAME.upper():
        raise FetchError("reserved file name: %s" % name)
    root = Path(root).resolve()
    target = (root / source_id / name).resolve()
    if root not in target.parents or target.parent != root / source_id:
        raise FetchError("target escapes data_raw root")
    if target.exists():
        raise FetchError("target already exists; refuse to overwrite: %s" % target)
    return target


def fetch(url, source_id, root, name=None, proxy=None):
    target = plan_target(url, source_id, root, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Environment proxies (HTTPS_PROXY, also honoured under -I) are ignored;
    # a proxy is used only when passed explicitly (WR-11).
    proxies = {"https": proxy} if proxy else {}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies),
                                         AllowlistRedirectHandler())
    deadline = time.monotonic() + TOTAL_TIMEOUT_S
    req = urllib.request.Request(url, headers={"User-Agent": "maison-veritas-fetch/1"})
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), prefix=".part-")
    try:
        sha = hashlib.sha256()
        total = 0
        with os.fdopen(fd, "wb") as out, opener.open(req, timeout=TIMEOUT_S) as resp:
            final_url = resp.geturl()
            if not host_allowed(final_url):
                raise FetchError("final URL not allowlisted: %s" % final_url)
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                if time.monotonic() > deadline:
                    raise FetchError("download exceeded %d s total" % TOTAL_TIMEOUT_S)
                total += len(chunk)
                if total > MAX_BYTES:
                    raise FetchError("download exceeds %d bytes" % MAX_BYTES)
                sha.update(chunk)
                out.write(chunk)
        os.chmod(tmp, 0o644)
        if target.exists():  # appeared during the download
            raise FetchError("target already exists; refuse to overwrite: %s" % target)
        os.replace(tmp, str(target))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    rec = {
        "url": url, "final_url": final_url, "source_id": source_id,
        "file": target.name, "sha256": sha.hexdigest(), "bytes": total,
        "retrieved_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(str(target.parent / MANIFEST_NAME), "a", encoding="utf-8") as m:
        m.write(json.dumps(rec, sort_keys=True) + "\n")
    return target


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch one raw data file from an official host into data_raw/<source_id>/.")
    ap.add_argument("--source-id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--name")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--proxy", help="explicit https proxy URL; environment "
                    "proxy variables are ignored")
    a = ap.parse_args(argv)
    try:
        p = fetch(a.url, a.source_id, Path(a.root), a.name, a.proxy)
    except (FetchError, urllib.error.URLError, OSError) as exc:
        print("fetch refused/failed: %s" % exc, file=sys.stderr)
        return 1
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
