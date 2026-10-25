"""The single write path for worksheet cells (D-14, D-15, D-18)."""
import datetime
import math
import re
from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from config.security import host_allowed, is_injection_string
from qa.lint import RangeTagIndex, lint_or_raise

MAX_TEXT = 32767
VALID_TAGS = ("LB", "MB")

class FormulaRecord(NamedTuple):
    sheet: str
    row: int
    col: int
    text: str
    value: object = None  # cached value written with the formula


class UnsafeCellError(ValueError):
    pass


_CELL_LIKE = re.compile(r"^([A-Za-z]{1,3})([0-9]+)$")
_SHEET_OK = re.compile(r"^[A-Za-z0-9_]+$")
_ADDR_OK = re.compile(r"^\$?[A-Z]{1,3}\$?[0-9]+$")
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


def _check_rc(rc, what, row, col):
    """XlsxWriter only warns on -1 (out of range) / -2 (too long); fail instead."""
    if rc not in (0, None):
        raise UnsafeCellError("%s at (%d, %d) was rejected by XlsxWriter (code %r)"
                              % (what, row, col, rc))


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
        _check_rc(ws.write_string(row, col, s, fmt), "write_string", row, col)

    def number(self, ws, row, col, x, fmt=None):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise UnsafeCellError("number() needs int or float, got %r" % (x,))
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            raise UnsafeCellError("NaN and infinity are not allowed")
        _check_rc(ws.write_number(row, col, x, fmt), "write_number", row, col)

    def date(self, ws, row, col, d, fmt):
        _check_rc(ws.write_datetime(row, col, datetime.datetime(d.year, d.month, d.day), fmt),
                  "write_datetime", row, col)

    def formula(self, ws, row, col, f, fmt, *, value):
        # type: (object, int, int, str, object, Union[int, float, str, bool]) -> None
        if not isinstance(value, (bool, int, float, str)):
            raise UnsafeCellError("formula cached value must be a number, "
                                  "text or bool, got %r" % (value,))
        if isinstance(value, float) and not math.isfinite(value):
            raise UnsafeCellError("formula cached value is NaN or infinity")
        lint_or_raise(f, ws.get_name(), self.tags)
        _check_rc(ws.write_formula(row, col, f, fmt, value), "write_formula", row, col)
        self._registry.append(FormulaRecord(ws.get_name(), row, col, f, value))

    def link(self, ws, row, col, url, fmt=None, string=None):
        if not host_allowed(url):
            raise UnsafeCellError("link host not on allowlist: %s" % url)
        if string is not None and (is_injection_string(string) or _has_bad_control(string)):
            raise UnsafeCellError("unsafe link display text")
        _check_rc(ws.write_url(row, col, url, fmt, string), "write_url", row, col)

    def internal_link(self, ws, row, col, sheet, cell, string, fmt=None, tip=None):
        """Navigation link to a cell in this workbook. Only 'internal:Sheet!A1'
        targets are written; HYPERLINK() stays banned."""
        if not isinstance(sheet, str) or not _SHEET_OK.match(sheet):
            raise UnsafeCellError("unsafe link sheet name: %r" % (sheet,))
        if not isinstance(cell, str) or not _ADDR_OK.match(cell):
            raise UnsafeCellError("unsafe link cell address: %r" % (cell,))
        for t in (string, tip):
            if t is not None and (is_injection_string(t) or _has_bad_control(t)):
                raise UnsafeCellError("unsafe link display text")
        target = "internal:%s!%s" % (sheet, cell.replace("$", ""))
        args = (row, col, target, fmt, string) + ((tip,) if tip is not None else ())
        _check_rc(ws.write_url(*args), "write_url", row, col)

    def target_of(self, name):
        """(sheet, first cell) of a registered defined name."""
        ref = self.names[name]
        sheet, _, addr = ref.lstrip("=").partition("!")
        return sheet.strip("'"), addr.split(":")[0].replace("$", "")

    def blank(self, ws, row, col, fmt):
        _check_rc(ws.write_blank(row, col, None, fmt), "write_blank", row, col)

    def define_name(self, name, ref):
        if not ref.startswith("=") or "[" in ref:
            raise UnsafeCellError("name reference must start with '=' and have no '[': %r" % ref)
        lint_or_raise(ref, "", None)  # banned functions, DDE '|', literals
        if _looks_like_cell(name):
            raise UnsafeCellError("defined name looks like a cell reference: %r" % name)
        if self.workbook.define_name(name, ref) != 0:
            raise UnsafeCellError("invalid defined name: %r" % name)
        self.names[name] = ref

    def insert_chart(self, ws, cell, chart, options=None):
        """Place a chart. Chart formulas are checked by the final-bytes scan.
        options: XlsxWriter x_offset / y_offset only."""
        if options and set(options) - {"x_offset", "y_offset"}:
            raise UnsafeCellError("unsupported chart option")
        if ws.insert_chart(cell, chart, options) != 0:
            raise UnsafeCellError("chart could not be inserted at %s" % cell)

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
        # XlsxWriter writes any string in these keys into <formula1>/<formula2>,
        # so every string is treated as a formula and linted (CR-01).
        for key in ("value", "source", "minimum", "maximum"):
            v = options.get(key)
            if isinstance(v, str):
                if not v.startswith("=") or "[" in v:
                    raise UnsafeCellError(
                        "validation %s must be a formula starting with '=' and "
                        "have no '['" % key)
                lint_or_raise(v, ws.get_name(), self.tags)
            elif isinstance(v, (list, tuple)):
                if not all(isinstance(x, str) and not is_injection_string(x)
                           and not _has_bad_control(x) for x in v):
                    raise UnsafeCellError("list source items must be safe strings")
        _check_rc(ws.data_validation(first_row, first_col, last_row, last_col, options),
                  "data_validation", first_row, first_col)
