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


# Selector functions return ONE of their branch arguments, so LB in one branch
# and MB in another is a selection, not a sum (CLAUDE.md LB/MB selector
# pattern). Value: indexes of the branch arguments (None = all from there on).
_SELECTORS = {
    "IF": (1, None),      # IF(cond, a, b)
    "CHOOSE": (1, None),  # CHOOSE(k, a, b, ...)
    "INDEX": (0, 1),      # INDEX(range, i[, j]): picks from the range
    "IFERROR": (0, None),  # IFERROR(a, b)
}
_EMPTY = frozenset()
_BOTH = frozenset(["LB", "MB"])


class _LbMbWalker(object):
    """Tracks which LB/MB tags a (sub)expression's value can carry.

    Each value is a set of alternatives; an alternative is the set of tags
    that end up combined in that outcome. Arithmetic, comparison and every
    non-selector function combine their operands (cartesian union); a
    selector only unions the alternatives of its branches. A violation is any
    alternative that holds both LB and MB, however deeply nested (CR-02).
    """

    def __init__(self, items, sheet, tags):
        self.items = [t for t in items if t.type != Token.WSPACE]
        self.sheet = sheet
        self.tags = tags
        self.pos = 0
        self.bad = False

    def _peek(self):
        return self.items[self.pos] if self.pos < len(self.items) else None

    def _combine(self, a, b):
        out = frozenset(x | y for x in a for y in b)
        if any(_BOTH <= x for x in out):
            self.bad = True
        return out

    def _ends_expr(self, tok):
        return tok is None or tok.type == Token.SEP or tok.subtype == Token.CLOSE

    def expr(self):
        """Returns (alternatives, raw tags if the expr is one range operand)."""
        alts = frozenset([_EMPTY])
        raw = None
        terms = 0
        while not self._ends_expr(self._peek()):
            tok = self._peek()
            if tok.type in (Token.OP_PRE, Token.OP_POST, Token.OP_IN):
                self.pos += 1
                continue
            t_alts, t_raw = self.term()
            terms += 1
            if terms == 1:  # a lone operand is not yet a combination
                alts, raw = t_alts, t_raw
            else:
                alts, raw = self._combine(alts, t_alts), None
        return alts, raw

    def term(self):
        tok = self._peek()
        self.pos += 1
        if tok.type == Token.OPERAND:
            if tok.subtype != Token.RANGE:
                return frozenset([_EMPTY]), None
            found = self.tags.tags_for(tok.value, self.sheet)
            return frozenset([frozenset(found)]), found
        if tok.type == Token.FUNC and tok.subtype == Token.OPEN:
            return self.func(_func_name(tok.value)), None
        if tok.subtype == Token.OPEN:  # parenthesis or array constant
            args = self.args()
            if len(args) == 1:
                return args[0]
            alts = frozenset([_EMPTY])
            for a, _ in args:  # (F20,F21) union or {..} array: combined
                alts = self._combine(alts, a)
            return alts, None
        return frozenset([_EMPTY]), None  # stray token: nothing tagged

    def args(self):
        out = []
        while True:
            out.append(self.expr())
            tok = self._peek()
            if tok is None:
                return out
            self.pos += 1
            if tok.subtype == Token.CLOSE:
                return out

    def func(self, name):
        args = self.args()
        if name not in _SELECTORS:
            alts = frozenset([_EMPTY])
            for a, _ in args:
                alts = self._combine(alts, a)
            return alts
        first, last = _SELECTORS[name]
        branch_idx = set(range(first, len(args) if last is None else last))
        result = set()
        for i, (a, raw) in enumerate(args):
            if i not in branch_idx:
                if any(_BOTH <= x for x in a):
                    self.bad = True
                continue
            if name == "INDEX" and raw is not None:
                # INDEX picks one cell of the range: each tag on its own.
                result |= set(frozenset([t]) for t in raw) or set([_EMPTY])
            else:
                result |= a
        return frozenset(result or [_EMPTY])

    def run(self):
        alts, _ = self.expr()
        while self._peek() is not None:  # unbalanced close: keep scanning
            self.pos += 1
            more, _ = self.expr()
            alts = self._combine(alts, more)
        if any(_BOTH <= x for x in alts):
            self.bad = True
        return self.bad


def _lb_mb(items, sheet, tags):
    if _LbMbWalker(items, sheet, tags).run():
        return ["formula combines LB- and MB-tagged ranges"]
    return []


def lint_or_raise(formula, sheet="", tags=None):
    problems = lint_formula(formula, sheet, tags)
    if problems:
        raise LintError(problems, formula)
