"""Write discipline: only xl/cells.py writes cell content; only xl/styles.py
adds formats.

The authoritative check is RUNTIME and type-based (RuntimeCallerGuard): it
wraps the public content-bearing XlsxWriter methods and asserts that every
external caller is the one sanctioned module, then builds every registered
target. That catches aliasing, getattr, functools.partial and any directory,
and it never touches ordinary file I/O.

The AST check below is a fast pre-filter over the only code that holds
worksheet objects (xl/ and build.py). Other packages must not import the
xlsxwriter Workbook at all.
"""
import ast
import os
import sys
import unittest
from typing import List
from unittest import mock

import xlsxwriter
import xlsxwriter.workbook
import xlsxwriter.worksheet

import build
from config.schema import ProvenanceError

ROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XLSXWRITER_DIR = os.path.realpath(os.path.dirname(xlsxwriter.__file__))

CELLS = "xl/cells.py"
STYLES = "xl/styles.py"
LAYOUT = "xl/layout.py"

# Public content-bearing methods -> the only module allowed to call them.
WORKSHEET_CALLERS = {
    "write": CELLS, "write_row": CELLS, "write_column": CELLS,
    "write_string": CELLS, "write_number": CELLS, "write_formula": CELLS,
    "write_array_formula": CELLS, "write_dynamic_array_formula": CELLS,
    "write_url": CELLS, "write_rich_string": CELLS, "write_comment": CELLS,
    "write_datetime": CELLS, "write_boolean": CELLS, "write_blank": CELLS,
    "merge_range": CELLS, "data_validation": CELLS, "add_table": CELLS,
    "insert_chart": CELLS, "insert_image": CELLS, "insert_textbox": CELLS,
    "insert_button": CELLS, "embed_image": CELLS,
    "conditional_format": STYLES,
    # Sheet settings that create _xlnm names or header/footer text.
    "set_header": LAYOUT, "set_footer": LAYOUT, "repeat_rows": LAYOUT,
    "repeat_columns": LAYOUT, "print_area": LAYOUT, "autofilter": LAYOUT,
}
WORKBOOK_CALLERS = {
    "define_name": CELLS,
    "add_format": STYLES,
    "set_custom_property": None,  # never used
}


class _CallerGuard(object):
    """Context manager that records disallowed external callers."""

    def __init__(self):
        self.violations = []  # type: List[str]
        self._patches = []

    def _wrap(self, cls, name, allowed):
        original = cls.__dict__[name]
        allowed_path = os.path.join(ROOT, allowed) if allowed else None
        violations = self.violations

        def shim(*args, **kwargs):
            caller = os.path.realpath(sys._getframe(1).f_code.co_filename)
            internal = caller.startswith(XLSXWRITER_DIR + os.sep)
            if not internal and caller != allowed_path:
                violations.append("%s.%s() called from %s (allowed: %s)"
                                  % (cls.__name__, name,
                                     os.path.relpath(caller, ROOT), allowed))
            return original(*args, **kwargs)

        self._patches.append(mock.patch.object(cls, name, shim))

    def __enter__(self):
        for name, allowed in sorted(WORKSHEET_CALLERS.items()):
            if name in xlsxwriter.worksheet.Worksheet.__dict__:
                self._wrap(xlsxwriter.worksheet.Worksheet, name, allowed)
        for name, allowed in sorted(WORKBOOK_CALLERS.items()):
            self._wrap(xlsxwriter.workbook.Workbook, name, allowed)
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        return False


class RuntimeCallerGuard(unittest.TestCase):
    def test_every_target_and_dataset(self):
        built = 0
        for target in sorted(build.TARGETS):
            for name in ("config", "fixtures"):
                with self.subTest(target=target, dataset=name):
                    with _CallerGuard() as guard:
                        try:
                            build.build_bytes(target, build.load_dataset(name))
                        except ProvenanceError:
                            continue  # e.g. spike refuses the real dataset
                    built += 1
                    self.assertEqual(guard.violations, [])
        self.assertGreaterEqual(built, 3)

    def test_guard_catches_bypasses(self):
        import functools

        def extra(wb):
            ws = wb.add_worksheet("Raw")
            w = ws.write_string  # aliasing
            w(0, 0, "x")
            getattr(ws, "write_" + "number")(1, 0, 1)
            functools.partial(ws.write_blank, 2, 0)(None)
            wb.define_name("Raw_Name", "=Raw!$A$1")
            ws.conditional_format(0, 0, 0, 0, {"type": "no_blanks",
                                               "format": None})
        with _CallerGuard() as guard:
            extra(xlsxwriter.Workbook(None, {"in_memory": True}))
        joined = "\n".join(guard.violations)
        for name in ("write_string", "write_number", "write_blank",
                     "define_name", "conditional_format"):
            self.assertIn(name, joined)


# --- Static pre-filter ----------------------------------------------------

STATIC_METHODS = (frozenset(n for n in WORKSHEET_CALLERS if n != "write")
                  | frozenset(WORKBOOK_CALLERS))
# Methods CellWriter re-exposes under the same name; callers hold it as `cells`.
CELLWRITER_METHODS = frozenset(["define_name", "insert_chart"])
WORKSHEET_NAMES = frozenset(["ws", "wsa", "wsc", "worksheet", "sheet"])
ALLOWED_FOR = dict(list(WORKSHEET_CALLERS.items()) + list(WORKBOOK_CALLERS.items()))


def find_violations(source, path):
    # type: (str, str) -> List[str]
    rel = path.replace(os.sep, "/")
    out = []  # type: List[str]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute):
            # Attribute references, not only calls, so aliasing is caught.
            name = node.attr
            owner = node.value
            if name == "write":
                # Bare write() is ordinary file I/O unless the receiver is a
                # worksheet-named variable.
                if (isinstance(owner, ast.Name) and owner.id in WORKSHEET_NAMES
                        and rel != CELLS):
                    out.append("%s:%d: write() outside %s" % (path, node.lineno, CELLS))
                continue
            if name not in STATIC_METHODS or rel == ALLOWED_FOR[name]:
                continue
            if (name in CELLWRITER_METHODS and isinstance(owner, ast.Name)
                    and owner.id == "cells"):
                continue
            out.append("%s:%d: %s outside %s"
                       % (path, node.lineno, name, ALLOWED_FOR[name]))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "getattr" and len(node.args) >= 2):
            arg = node.args[1]
            if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                out.append("%s:%d: dynamic getattr()" % (path, node.lineno))
            elif arg.value in STATIC_METHODS or arg.value == "write":
                out.append("%s:%d: getattr(.., %r)" % (path, node.lineno, arg.value))
    return out


def find_xlsxwriter_imports(source, path):
    # type: (str, str) -> List[str]
    """Only xlsxwriter.utility may be imported outside xl/ and build.py."""
    out = []  # type: List[str]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "xlsxwriter" or (a.name.startswith("xlsxwriter.")
                                              and a.name != "xlsxwriter.utility"):
                    out.append("%s:%d: import %s" % (path, node.lineno, a.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "xlsxwriter" or (
                    node.module.startswith("xlsxwriter.")
                    and node.module != "xlsxwriter.utility"):
                out.append("%s:%d: from %s import ..." % (path, node.lineno, node.module))
    return out


def _py_files(*dirs):
    paths = []
    for d in dirs:
        for dirpath, dirnames, files in os.walk(os.path.join(ROOT, d)):
            dirnames.sort()
            for f in sorted(files):
                if f.endswith(".py"):
                    paths.append(os.path.join(dirpath, f))
    return paths


def targets():
    paths = _py_files("xl")
    b = os.path.join(ROOT, "build.py")
    if os.path.exists(b):
        paths.append(b)
    return paths


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class StaticPreFilter(unittest.TestCase):
    def test_checker_flags_synthetic(self):
        bad = [
            ('ws.write_string(0,0,"x")', "xl/sheets/a.py"),
            ("wb.add_format({})", "xl/sheets/a.py"),
            ("wb.define_name('a','=b')", "build.py"),
            ("w = ws.write_string\nw(0, 0, '=x')", "xl/sheets/a.py"),
            ("getattr(ws, 'write_' + 'number')(0, 0, 1)", "xl/sheets/a.py"),
            ("getattr(ws, 'write_number')(0, 0, 1)", "xl/sheets/a.py"),
            ("functools.partial(ws.write_formula, 0, 0)('=1')", "xl/a.py"),
            ("list(map(ws.write_string, [0], [0], ['x']))", "xl/a.py"),
            ("cells = wb\ncells.add_format({})", "xl/a.py"),
            ("self.define_name('a', '=b')", "xl/sheets/a.py"),
            ("ws.write(0, 0, 'x')", "xl/sheets/a.py"),
            ("ws.conditional_format(0, 0, 0, 0, {})", "xl/sheets/a.py"),
            ("ws.insert_chart('A1', ch)", "xl/sheets/a.py"),
            ("ws.set_footer('x')", "xl/sheets/a.py"),
            ('ws.write_string(0,0,"x")', "xl/notxl/cells.py"),
            ("wb.add_format({})", "qa/xl/styles.py"),
        ]
        for src, path in bad:
            with self.subTest(src=src, path=path):
                self.assertTrue(find_violations(src, path), src)

    def test_checker_allows_sanctioned(self):
        ok = [
            ("cells.define_name('a','=b')", "xl/sheets/a.py"),
            ("cells.insert_chart(ws, 'A1', ch)", "xl/sheets/a.py"),
            ('ws.write_string(0,0,"x")', "xl/cells.py"),
            ("wb.add_format({})", "xl/styles.py"),
            ("ws.conditional_format(0, 0, 0, 0, {})", "xl/styles.py"),
            ("ws.set_footer('x')", "xl/layout.py"),
            ("fh.write(b'x')", "build.py"),
            ("sys.stderr.write('x')", "build.py"),
            ("buf.write(data)", "build.py"),
        ]
        for src, path in ok:
            with self.subTest(src=src, path=path):
                self.assertEqual(find_violations(src, path), [], src)

    def test_real_tree_clean(self):
        problems = []
        for p in targets():
            problems.extend(find_violations(_read(p), os.path.relpath(p, ROOT)))
        self.assertEqual(problems, [])

    def test_no_workbook_imports_outside_xl(self):
        self.assertTrue(find_xlsxwriter_imports("import xlsxwriter", "qa/a.py"))
        self.assertTrue(find_xlsxwriter_imports(
            "from xlsxwriter.workbook import Workbook", "qa/a.py"))
        self.assertEqual(find_xlsxwriter_imports(
            "from xlsxwriter.utility import xl_rowcol_to_cell", "qa/a.py"), [])
        problems = []
        for p in _py_files("qa", "checkmodel", "tools", "config",
                           os.path.join("tests", "fixtures")):
            problems.extend(find_xlsxwriter_imports(_read(p), os.path.relpath(p, ROOT)))
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
