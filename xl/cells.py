"""The single write path for worksheet cells (D-14, D-15, D-18)."""
import datetime
import math
import re
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from config.security import host_allowed, is_injection_string
from qa.lint import RangeTagIndex, lint_or_raise

MAX_TEXT = 32767
VALID_TAGS = ("LB", "MB")

FormulaRecord = NamedTuple("FormulaRecord", [
    ("sheet", str), ("row", int), ("col", int), ("text", str)])


class UnsafeCellError(ValueError):
    pass


_CELL_LIKE = re.compile(r"^([A-Za-z]{1,3})([0-9]+)$")
_R1C1_LIKE = re.compile(r"^[Rr]([0-9]*)([Cc]([0-9]*))?$|^[Cc][0-9]*$")


def _looks_like_cell(name):
    """True if Excel would read the name as an A1 or R1C1 reference."""
    if _R1C1_LIKE.match(name):
        return True
    m = _CELL_LIKE.match(name)
    if m is None:
        return False
    col = 0
    for ch in m.group(1).upper():
        col = col * 26 + (ord(ch) - 64)
    return col <= 16384 and 1 <= int(m.group(2)) <= 1048576


def _has_bad_control(s):
    return any((ord(c) < 32 and c != "\n") or ord(c) == 127 for c in s)


class CellWriter(object):
    def __init__(self, workbook):
        self.workbook = workbook
        self.tags = RangeTagIndex()
        self.names = {}  # type: Dict[str, str]
        self._registry = []  # type: List[FormulaRecord]

    @property
    def registry(self):
        # type: () -> Tuple[FormulaRecord, ...]
        return tuple(self._registry)

    def text(self, ws, row, col, s, fmt=None):
        if is_injection_string(s):
            raise UnsafeCellError("text looks like a formula: %r" % s[:40])
        if _has_bad_control(s):
            raise UnsafeCellError("text contains a control character")
        if len(s) > MAX_TEXT:
            raise UnsafeCellError("text longer than %d characters" % MAX_TEXT)
        ws.write_string(row, col, s, fmt)

    def number(self, ws, row, col, x, fmt=None):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise UnsafeCellError("number() needs int or float, got %r" % (x,))
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            raise UnsafeCellError("NaN and infinity are not allowed")
        ws.write_number(row, col, x, fmt)

    def date(self, ws, row, col, d, fmt):
        ws.write_datetime(row, col, datetime.datetime(d.year, d.month, d.day), fmt)

    def formula(self, ws, row, col, f, fmt, *, value):
        # type: (object, int, int, str, object, Union[int, float, str, bool]) -> None
        lint_or_raise(f, ws.get_name(), self.tags)
        self._registry.append(FormulaRecord(ws.get_name(), row, col, f))
        ws.write_formula(row, col, f, fmt, value)

    def link(self, ws, row, col, url, fmt=None, string=None):
        if not host_allowed(url):
            raise UnsafeCellError("link host not on allowlist: %s" % url)
        if string is not None and (is_injection_string(string) or _has_bad_control(string)):
            raise UnsafeCellError("unsafe link display text")
        ws.write_url(row, col, url, fmt, string)

    def blank(self, ws, row, col, fmt):
        ws.write_blank(row, col, None, fmt)

    def define_name(self, name, ref):
        if not ref.startswith("=") or "[" in ref:
            raise UnsafeCellError("name reference must start with '=' and have no '[': %r" % ref)
        if _looks_like_cell(name):
            raise UnsafeCellError("defined name looks like a cell reference: %r" % name)
        if self.workbook.define_name(name, ref) != 0:
            raise UnsafeCellError("invalid defined name: %r" % name)
        self.names[name] = ref

    def tag(self, sheet, first_row, first_col, last_row, last_col, tag):
        if tag not in VALID_TAGS:
            raise UnsafeCellError("tag must be one of %s" % (VALID_TAGS,))
        self.tags.add(sheet, first_row, first_col, last_row, last_col, tag)

    def tag_name(self, name, tag):
        ref = self.names.get(name)
        if ref is None:
            raise UnsafeCellError("unknown defined name: %r" % name)
        from qa.lint import _REF_RE, _unquote  # local: reuse reference parser
        body = ref[1:]
        probe = RangeTagIndex()
        m = _REF_RE.match(body)
        if m is None or not m.group("sheet"):
            raise UnsafeCellError("cannot tag non-range name: %r" % name)
        sheet = _unquote(m.group("sheet"))
        ext = probe._resolve(body, sheet)
        if ext is None:
            raise UnsafeCellError("cannot resolve name range: %r" % name)
        self.tag(sheet, ext[1][0], ext[1][1], ext[1][2], ext[1][3], tag)
        self.tags.add_name(name, sheet, *ext[1])

    def validation(self, ws, first_row, first_col, last_row, last_col, options):
        src = options.get("source")
        if isinstance(src, str):
            if not src.startswith("=") or "[" in src:
                raise UnsafeCellError("range source must start with '=' and have no '['")
        elif isinstance(src, (list, tuple)):
            if not all(isinstance(x, str) and not is_injection_string(x) for x in src):
                raise UnsafeCellError("list source items must be safe strings")
        ws.data_validation(first_row, first_col, last_row, last_col, options)
