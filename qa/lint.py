"""Tokenizer-based formula lint (D-15) with an LB/MB range tag index."""
import re
from typing import Dict, FrozenSet, List, Optional, Tuple

from openpyxl.formula import Tokenizer
from openpyxl.formula.tokenizer import Token
from xlsxwriter.utility import xl_cell_to_rowcol

from config.security import ALLOWED_NUMERIC_LITERALS, BANNED_FUNCTIONS

MAX_ROW = 1048575
MAX_COL = 16383

Extent = Tuple[int, int, int, int]


class LintError(ValueError):
    def __init__(self, problems, formula=""):
        self.problems = tuple(problems)
        self.formula = formula
        ValueError.__init__(self, "formula lint failed for %r: %s"
                            % (formula, "; ".join(self.problems)))


_SHEET = r"(?:(?P<sheet>'(?:[^']|'')+'|[A-Za-z0-9_.]+)!)?"
_CELL = r"\$?[A-Za-z]{1,3}\$?[0-9]+"
_COL = r"\$?[A-Za-z]{1,3}"
_ROW = r"\$?[0-9]+"
_REF_RE = re.compile(
    r"^" + _SHEET + r"(?:(?P<c1>" + _CELL + r")(?::(?P<c2>" + _CELL + r"))?"
    r"|(?P<k1>" + _COL + r"):(?P<k2>" + _COL + r")"
    r"|(?P<r1>" + _ROW + r"):(?P<r2>" + _ROW + r"))$")


def _col_index(letters):
    n = 0
    for ch in letters.replace("$", "").upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _unquote(sheet):
    if sheet.startswith("'") and sheet.endswith("'"):
        return sheet[1:-1].replace("''", "'")
    return sheet


class RangeTagIndex(object):
    def __init__(self):
        self._ranges = []  # type: List[Tuple[str, Extent, str]]
        self._names = {}  # type: Dict[str, Tuple[str, Extent]]

    def add(self, sheet, first_row, first_col, last_row, last_col, tag):
        self._ranges.append((sheet, (first_row, first_col, last_row, last_col), tag))

    def add_name(self, name, sheet, first_row, first_col, last_row, last_col):
        self._names[name.upper()] = (
            sheet, (first_row, first_col, last_row, last_col))

    def name_extent(self, name):
        return self._names.get(name.upper())

    def tags_for(self, operand, current_sheet):
        # type: (str, str) -> FrozenSet[str]
        ext = self._resolve(operand, current_sheet)
        if ext is None:
            return frozenset()
        sheet, (r1, c1, r2, c2) = ext
        found = set()
        for s, (a, b, c, d), tag in self._ranges:
            if s == sheet and not (r2 < a or c < r1 or c2 < b or d < c1):
                found.add(tag)
        return frozenset(found)

    def _resolve(self, operand, current_sheet):
        m = _REF_RE.match(operand)
        if m is None:
            return self._names.get(operand.upper())
        sheet = _unquote(m.group("sheet")) if m.group("sheet") else current_sheet
        if m.group("c1"):
            r1, c1 = xl_cell_to_rowcol(m.group("c1").replace("$", ""))
            c2cell = m.group("c2") or m.group("c1")
            r2, c2 = xl_cell_to_rowcol(c2cell.replace("$", ""))
            return sheet, (min(r1, r2), min(c1, c2), max(r1, r2), max(c1, c2))
        if m.group("k1"):
            a, b = _col_index(m.group("k1")), _col_index(m.group("k2"))
            return sheet, (0, min(a, b), MAX_ROW, max(a, b))
        a = int(m.group("r1").replace("$", "")) - 1
        b = int(m.group("r2").replace("$", "")) - 1
        return sheet, (min(a, b), 0, max(a, b), MAX_COL)


def _func_name(value):
    name = value[:-1] if value.endswith("(") else value
    name = name.upper()
    for prefix in ("_XLFN.", "_XLWS."):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name


def lint_formula(formula, sheet="", tags=None):
    # type: (str, str, Optional[RangeTagIndex]) -> List[str]
    if not formula.startswith("="):
        return ["formula must start with '='"]
    try:
        items = Tokenizer(formula).items
    except Exception as exc:  # tokenizer rejects e.g. '|' and '#'
        return ["unparseable formula: %s" % exc]
    problems = []  # type: List[str]
    for i, tok in enumerate(items):
        pos = "token %d" % i
        if tok.type == Token.OPERAND and tok.subtype == Token.NUMBER:
            try:
                num = float(tok.value)
            except ValueError:
                num = None
            if num is None or num not in ALLOWED_NUMERIC_LITERALS:
                problems.append("%s: numeric literal %s not allowed (only 0 or 1)"
                                % (pos, tok.value))
        elif tok.type == Token.FUNC and tok.subtype == Token.OPEN:
            name = _func_name(tok.value)
            if name in BANNED_FUNCTIONS:
                problems.append("%s: banned function %s" % (pos, name))
        elif tok.type == Token.OPERAND and tok.subtype == Token.RANGE:
            if "[" in tok.value:
                problems.append("%s: external or structured reference %s"
                                % (pos, tok.value))
            if tok.value.endswith("#"):
                problems.append("%s: spill reference %s" % (pos, tok.value))
        elif tok.type == Token.OPERAND and tok.subtype == Token.TEXT:
            low = tok.value.lower()
            if "://" in low or "file:" in low or tok.value.strip('"').startswith("\\\\"):
                problems.append("%s: text operand looks like a URL or path" % pos)
    # whole-string DDE check outside quoted text
    stripped = re.sub(r'"(?:[^"]|"")*"', '""', formula)
    if "|" in stripped:
        problems.append("pipe character outside text (DDE risk)")
    if "cmd|" in stripped.lower():
        problems.append("cmd| DDE pattern")
    if tags is not None:
        problems.extend(_lb_mb(items, sheet, tags))
    return problems


def _lb_mb(items, sheet, tags):
    seen = set()
    for tok in items:
        if tok.type == Token.OPERAND and tok.subtype == Token.RANGE:
            seen |= tags.tags_for(tok.value, sheet)
    if "LB" in seen and "MB" in seen:
        first_func = next((t for t in items if t.type == Token.FUNC
                           and t.subtype == Token.OPEN), None)
        selector = first_func is not None and _func_name(first_func.value) in (
            "CHOOSE", "INDEX")
        arith = any(t.type == Token.OP_IN and t.value in "+-*/^&" for t in items)
        if not selector or arith:
            return ["formula combines LB- and MB-tagged ranges"]
    return []


def lint_or_raise(formula, sheet="", tags=None):
    problems = lint_formula(formula, sheet, tags)
    if problems:
        raise LintError(problems, formula)
