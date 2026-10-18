"""The build needs no network, and the build trees import nothing networked."""
import ast
import contextlib
import io
import os
import socket
import tempfile
import unittest
from unittest import mock

import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_IMPORTS = frozenset([
    "abc", "argparse", "ast", "collections", "dataclasses", "datetime", "enum",
    "functools", "hashlib", "io", "itertools", "json", "math", "os", "pathlib",
    "re", "sys", "tempfile", "typing", "urllib", "xml", "zipfile",
    "xlsxwriter", "openpyxl", "config", "xl", "qa", "checkmodel", "tests",
])
FORBIDDEN_MODULES = ("ftplib", "http.client", "requests", "socket", "urllib.request")
PACKAGES = ("config", "xl", "qa", "checkmodel")


def _py_files():
    files = [os.path.join(ROOT, "build.py")]
    for pkg in PACKAGES:
        top = os.path.join(ROOT, pkg)
        if not os.path.isdir(top):
            continue
        for dirpath, dirnames, names in os.walk(top):
            dirnames.sort()
            files.extend(os.path.join(dirpath, n) for n in sorted(names)
                         if n.endswith(".py"))
    return files


def _imports(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module
            for a in node.names:
                yield "%s.%s" % (node.module, a.name)


def _forbidden(mod):
    return any(mod == f or mod.startswith(f + ".") for f in FORBIDDEN_MODULES)


class Offline(unittest.TestCase):
    def test_build_with_sockets_disabled(self):
        def deny(*a, **k):
            raise OSError("network disabled in test")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(socket.socket, "connect", deny), \
                mock.patch.object(socket, "create_connection", deny), \
                mock.patch.object(socket, "getaddrinfo", deny), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = build.main(["--dataset", "fixtures",
                             "--out", os.path.join(tmp, "o.xlsx")])
        self.assertEqual(rc, 0)

    def test_import_audit(self):
        problems = []
        for path in _py_files():
            rel = os.path.relpath(path, ROOT)
            for mod in _imports(path):
                top = mod.split(".")[0]
                if _forbidden(mod):
                    problems.append("%s imports forbidden %s" % (rel, mod))
                elif top not in ALLOWED_IMPORTS and mod.count(".") == 0:
                    problems.append("%s imports unlisted %s" % (rel, mod))
                if top == "tests" and rel != "build.py":
                    problems.append("%s imports tests" % rel)
                if top == "xl" and rel.startswith("checkmodel"):
                    problems.append("%s imports xl" % rel)
        self.assertEqual(problems, [])

    def test_checkmodel_audited_and_fixtures_only_via_dataset(self):
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "checkmodel")))
        self.assertIn("checkmodel", PACKAGES)
        self.assertIn("checkmodel", ALLOWED_IMPORTS)
        audited = [os.path.relpath(p, ROOT) for p in _py_files()]
        for rel in ("xl/sheets/spike.py", "xl/macc.py", "xl/charts.py",
                    "checkmodel/macc_reference.py"):
            self.assertIn(rel, audited)
        for path in _py_files():
            rel = os.path.relpath(path, ROOT)
            if rel.startswith(("xl", "checkmodel", "qa", "config")):
                self.assertFalse(
                    [m for m in _imports(path) if m.split(".")[0] == "tests"],
                    rel)


if __name__ == "__main__":
    unittest.main()
