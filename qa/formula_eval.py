"""Safe stdlib formula evaluator for QA (plan 02-14, closes WR-03).

Re-computes workbook formula strings from their literal inputs, ignoring the
cached values, so a wrong reference inside a formula string is caught.
Test-time guard only: it reads workbook bytes and never saves anything.
It does not import the reference model (checkmodel).
"""
import io
import re
from typing import Dict, List, Tuple

import openpyxl
from openpyxl.formula import Tokenizer
from openpyxl.utils import range_boundaries


class FormulaEvalError(ValueError):
    """Unsupported token, unknown function, cycle or Excel error value."""


def _flat(args):
    for x in args:
        if isinstance(x, list):
            for y in _flat(x):
                yield y
        else:
            yield x


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _SUM(*a):
    return sum(x for x in _flat(a) if _num(x))


def _AVERAGE(*a):
    v = [x for x in _flat(a) if _num(x)]
    if not v:
        raise FormulaEvalError("#DIV/0! in AVERAGE")
    return sum(v) / len(v)


def _MIN(*a):
    v = [x for x in _flat(a) if _num(x)]
    return min(v) if v else 0


def _MAX(*a):
    v = [x for x in _flat(a) if _num(x)]
    return max(v) if v else 0


def _ABS(x):
    return abs(x)


def _AND(*a):
    return all(bool(x) for x in _flat(a) if x is not None)


def _MATCH(x, rng, kind=1):
    if kind != 1:
        raise FormulaEvalError("MATCH only supports type 1")
    pos = None
    for i, b in enumerate(_flat([rng])):
        if _num(b) and _num(x) and b <= x:
            pos = i + 1
    if pos is None:
        raise FormulaEvalError("#N/A in MATCH")
    return pos


def _INDEX(rng, k, col=None):
    if col is not None:
        raise FormulaEvalError("INDEX supports 1-D ranges only")
    vals = list(_flat([rng]))
    k = int(k)
    if k < 1 or k > len(vals):
        raise FormulaEvalError("#REF! in INDEX")
    return vals[k - 1]


def _CHOOSE(i, *a):
    i = int(i)
    if i < 1 or i > len(a):
        raise FormulaEvalError("#VALUE! in CHOOSE")
    return a[i - 1]


def _IF(c, a, b=False):
    return a if c else b


_FUNCS = {"SUM": _SUM, "AVERAGE": _AVERAGE, "MIN": _MIN, "MAX": _MAX,
          "ABS": _ABS, "AND": _AND, "IF": _IF, "MATCH": _MATCH,
          "INDEX": _INDEX, "CHOOSE": _CHOOSE}
SUPPORTED_FUNCTIONS = frozenset(_FUNCS)

_INFIX = {"+": "+", "-": "-", "*": "*", "/": "/", "=": "==", "<>": "!=",
          "<": "<", ">": ">", "<=": "<=", ">=": ">="}
_SHEET_REF = re.compile(r"^(?:(?P<s>'(?:[^']|'')+'|[A-Za-z0-9_.]+)!)?"
                        r"(?P<r>\$?[A-Za-z]{1,3}\$?[0-9]+(?::\$?[A-Za-z]{1,3}\$?[0-9]+)?)$")
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _unquote(s):
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1].replace("''", "'")
    return s


class FormulaEvaluator(object):
    def __init__(self, wb_formulas, overrides=None):
        self.wb = wb_formulas
        self.overrides = dict(overrides or {})
        self._cache = {}  # type: Dict[Tuple[str, str], object]
        self._busy = set()
        self._names = {}
        for k, v in wb_formulas.defined_names.items():
            self._names[k] = v.attr_text

    def name_target(self, name):
        if name not in self._names:
            raise FormulaEvalError("unknown name %r" % name)
        sheet, ref = self._names[name].rsplit("!", 1)
        return _unquote(sheet), ref.replace("$", "")

    # -- cell and range resolution ------------------------------------
    def value(self, sheet, coord):
        coord = coord.replace("$", "").upper()
        key = (sheet, coord)
        if key in self.overrides:
            return self.overrides[key]
        if key in self._cache:
            return self._cache[key]
        if key in self._busy:
            raise FormulaEvalError("circular reference at %s!%s" % key)
        raw = self.wb[sheet][coord].value
        if isinstance(raw, str) and raw.startswith("="):
            self._busy.add(key)
            try:
                val = self._eval(sheet, raw)
            finally:
                self._busy.discard(key)
        elif raw is None or isinstance(raw, (str, int, float, bool)):
            val = raw
        else:
            raise FormulaEvalError("unsupported cell content at %s!%s: %s"
                                   % (sheet, coord, type(raw).__name__))
        self._cache[key] = val
        return val

    def _ref(self, sheet, ref):
        ref = ref.replace("$", "").upper()
        if ":" not in ref:
            v = self.value(sheet, ref)
            return 0 if v is None else v
        c1, r1, c2, r2 = range_boundaries(ref)
        out = []
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                out.append(self.value(sheet, openpyxl.utils.get_column_letter(c) + str(r)))
        return out

    # -- translation ---------------------------------------------------
    def _operand(self, sheet, text):
        if "__" in text or "." in text.split("!")[0] and not _SHEET_REF.match(text):
            raise FormulaEvalError("rejected identifier %r" % text)
        m = _SHEET_REF.match(text)
        if m:
            s = _unquote(m.group("s")) if m.group("s") else sheet
            if s not in self.wb.sheetnames:
                raise FormulaEvalError("unknown sheet %r" % s)
            return "_R(%r,%r)" % (s, m.group("r"))
        if _NAME.match(text):
            s, r = self.name_target(text)
            return "_R(%r,%r)" % (s, r)
        raise FormulaEvalError("unsupported operand %r" % text)

    def _translate(self, sheet, formula):
        tok = Tokenizer(formula)
        parts = []
        for t in tok.items:
            ty, st, v = t.type, t.subtype, t.value
            if ty == "WHITE-SPACE":
                continue
            if ty == "OPERAND":
                if st == "NUMBER":
                    parts.append(repr(float(v)) if re.search(r"[.eE]", v) else v)
                elif st == "TEXT":
                    parts.append(repr(v[1:-1].replace('""', '"')))
                elif st == "LOGICAL":
                    parts.append("True" if v.upper() == "TRUE" else "False")
                elif st == "RANGE":
                    parts.append(self._operand(sheet, v))
                else:
                    raise FormulaEvalError("unsupported operand type %s %r" % (st, v))
            elif ty == "FUNC":
                if st == "OPEN":
                    name = v[:-1]
                    if name.upper() != name or name not in SUPPORTED_FUNCTIONS:
                        raise FormulaEvalError("unsupported function %r" % name)
                    parts.append("_F_%s(" % name)
                else:
                    parts.append(")")
            elif ty == "SEP":
                if st != "ARG":
                    raise FormulaEvalError("unsupported separator %r" % v)
                parts.append(",")
            elif ty == "PAREN":
                parts.append(v)
            elif ty == "OPERATOR-INFIX":
                if v not in _INFIX:
                    raise FormulaEvalError("unsupported operator %r" % v)
                parts.append(_INFIX[v])
            elif ty == "OPERATOR-PREFIX":
                if v not in ("-", "+"):
                    raise FormulaEvalError("unsupported prefix %r" % v)
                parts.append(v)
            else:
                raise FormulaEvalError("unsupported token %s %r" % (ty, v))
        return " ".join(parts)

    def _eval(self, sheet, formula):
        py = self._translate(sheet, formula)
        env = {"__builtins__": {},
               "_R": lambda s, r: self._ref(s, r)}
        for n, f in _FUNCS.items():
            env["_F_" + n] = f
        try:
            return eval(compile(py, "<formula>", "eval"), env, {})
        except FormulaEvalError:
            raise
        except ZeroDivisionError:
            raise FormulaEvalError("#DIV/0! in %s" % formula)
        except Exception as e:
            raise FormulaEvalError("cannot evaluate %s: %s" % (formula, e))


def _close(got, want, rel_tol):
    if _num(got) and _num(want):
        return abs(got - want) <= rel_tol * max(1.0, abs(want))
    return got == want


def compare_cached(data, rel_tol=1e-9, overrides=None):
    """Return (mismatches, n_formulas) for the workbook bytes.

    Each formula is evaluated from its string and compared with the cached
    value. Evaluation errors are reported as mismatches, not raised.
    """
    wf = openpyxl.load_workbook(io.BytesIO(data))
    wv = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ev = FormulaEvaluator(wf, overrides)
    bad = []  # type: List[str]
    n = 0
    for ws in wf:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    n += 1
                    want = wv[ws.title][c.coordinate].value
                    try:
                        got = ev.value(ws.title, c.coordinate)
                    except FormulaEvalError as e:
                        bad.append("%s!%s %s ERROR %s" % (ws.title, c.coordinate, c.value[:80], e))
                        continue
                    if not _close(got, want, rel_tol):
                        bad.append("%s!%s %s got %r want %r" % (
                            ws.title, c.coordinate, c.value[:80], got, want))
    return bad, n
