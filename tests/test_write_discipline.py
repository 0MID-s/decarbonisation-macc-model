"""AST guard: only xl/cells.py may write cells; only xl/styles.py adds formats."""
import ast
import os
import unittest
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRITE_METHODS = frozenset([
    "write", "write_row", "write_column", "write_string", "write_number",
    "write_formula", "write_array_formula", "write_dynamic_array_formula",
    "write_url", "write_rich_string", "write_comment", "write_datetime",
    "write_boolean", "write_blank", "merge_range", "define_name",
    "data_validation",
])


def find_violations(source, path):
    # type: (str, str) -> List[str]
    norm = path.replace(os.sep, "/")
    in_cells = norm.endswith("xl/cells.py")
    in_styles = norm.endswith("xl/styles.py")
    out = []  # type: List[str]
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        name = node.func.attr
        owner = node.func.value
        if name in WRITE_METHODS and not in_cells:
            if name == "define_name" and isinstance(owner, ast.Name) and owner.id == "self":
                continue
            out.append("%s:%d: %s() outside xl/cells.py" % (path, node.lineno, name))
        if name == "add_format" and not in_styles:
            out.append("%s:%d: add_format() outside xl/styles.py" % (path, node.lineno))
    return out


def targets():
    paths = []
    for d in ("xl", "qa", "checkmodel", "tools"):
        full = os.path.join(ROOT, d)
        for dirpath, dirnames, files in os.walk(full):
            dirnames.sort()
            for f in sorted(files):
                if f.endswith(".py"):
                    paths.append(os.path.join(dirpath, f))
    build = os.path.join(ROOT, "build.py")
    if os.path.exists(build):
        paths.append(build)
    return paths


class WriteDiscipline(unittest.TestCase):
    def test_checker_flags_synthetic(self):
        self.assertTrue(find_violations('ws.write_string(0,0,"x")', "xl/sheets/a.py"))
        self.assertTrue(find_violations("wb.add_format({})", "xl/sheets/a.py"))
        self.assertTrue(find_violations("wb.define_name('a','=b')", "build.py"))
        self.assertEqual(find_violations('ws.write_string(0,0,"x")', "xl/cells.py"), [])
        self.assertEqual(find_violations("wb.add_format({})", "xl/styles.py"), [])

    def test_real_tree_clean(self):
        problems = []
        for p in targets():
            with open(p, encoding="utf-8") as fh:
                problems.extend(find_violations(fh.read(), os.path.relpath(p, ROOT)))
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
