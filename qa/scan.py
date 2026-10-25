"""Default-deny OOXML security scan run on the final bytes of every build.

SET-03 / D-13 / D-14. Stdlib plus config.security only. A workbook passes only
if every part, content type, relationship, formula and string is on a known-safe
list; anything else is a finding. Formulas are checked wherever they can
appear: worksheet cells, defined names, data validations, conditional formats
and chart references. scan_xlsx_bytes returns findings (empty =
clean); scan_or_raise raises ScanError.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Tuple
from urllib.parse import urlsplit

from config.security import BANNED_FUNCTIONS, host_allowed, is_injection_string

PART_ALLOWLIST = (
    r"\[Content_Types\]\.xml",
    r"_rels/\.rels",
    r"docProps/app\.xml",
    r"docProps/core\.xml",
    r"xl/workbook\.xml",
    r"xl/_rels/workbook\.xml\.rels",
    r"xl/styles\.xml",
    r"xl/theme/theme1\.xml",
    r"xl/sharedStrings\.xml",
    r"xl/worksheets/sheet\d+\.xml",
    r"xl/worksheets/_rels/sheet\d+\.xml\.rels",
    r"xl/drawings/drawing\d+\.xml",
    r"xl/drawings/_rels/drawing\d+\.xml\.rels",
    r"xl/charts/chart\d+\.xml",
)  # type: Tuple[str, ...]

MAIN_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
MAX_TOTAL = 50 * 1024 * 1024
MAX_PART = 20 * 1024 * 1024
FORBIDDEN_CT = ("vbaproject", "macroenabled", "macrosheet", "externallink", "oleobject",
                "activex", "connections", "querytable", "vnd.ms-office.vba")
FORBIDDEN_REL = ("vbaproject", "externallink", "oleobject", "macro", "connections")
FORBIDDEN_WB_TAGS = ("externalReferences", "oleSize", "webPublishItems")
FORBIDDEN_SHEET_TAGS = ("oleObjects", "controls", "legacyDrawing", "webPublishItems")
# Formula-bearing elements in sheet parts: cell formulas, data-validation
# formula1/formula2 and conditional-format formula (CR-01).
FORMULA_TAGS = ("f", "formula", "formula1", "formula2")
_ALLOW_RES = [re.compile("^" + p + "$") for p in PART_ALLOWLIST]
_FUNC_RE = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in sorted(BANNED_FUNCTIONS)) + r")\s*\(")


class ScanError(RuntimeError):
    def __init__(self, findings):
        self.findings = tuple(findings)
        super().__init__("security scan failed: " + "; ".join(self.findings))


def _local(tag):
    return tag.split("}")[-1]


def _open(data):
    return zipfile.ZipFile(io.BytesIO(data))


def part_names(data):
    # type: (bytes) -> List[str]
    with _open(data) as z:
        return sorted(i.filename for i in z.infolist())


_ESC_RE = re.compile(r"_x([0-9A-Fa-f]{4})_")


def _unescape(s):
    """Decode OOXML _xHHHH_ escapes the way Excel does (e.g. _x000D_ = CR)."""
    return _ESC_RE.sub(lambda m: chr(int(m.group(1), 16)), s)


def _text(el):
    return _unescape("".join(t.text or "" for t in el.iter() if _local(t.tag) == "t"))


def scan_xlsx_bytes(data):
    # type: (bytes) -> List[str]
    findings = []  # type: List[str]
    try:
        z = _open(data)
    except (zipfile.BadZipFile, ValueError) as exc:
        return ["not a valid zip container: %s" % exc]
    with z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        try:
            if z.testzip() is not None:
                findings.append("zip integrity check failed")
        except Exception as exc:  # corrupt member
            findings.append("zip integrity check failed: %s" % exc)
            return findings
        seen = set()
        for n in names:
            if n in seen:
                findings.append("duplicate part name: %s" % n)
            seen.add(n)
            if ".." in n.split("/") or n.startswith("/") or "\\" in n or ":" in n:
                findings.append("unsafe part name: %s" % n)
        if sum(i.file_size for i in infos) > MAX_TOTAL:
            findings.append("total uncompressed size exceeds cap")
        for i in infos:
            if i.file_size > MAX_PART:
                findings.append("part exceeds size cap: %s" % i.filename)
        if findings:
            return findings
        for n in sorted(set(names)):
            if not any(r.match(n) for r in _ALLOW_RES):
                findings.append("part not on allowlist: %s" % n)
        blobs = {}
        for n in sorted(set(names)):
            raw = z.read(n)
            blobs[n] = raw
            up = raw.upper()
            if b"<!DOCTYPE" in up or b"<!ENTITY" in up:
                findings.append("DOCTYPE/ENTITY declaration in part: %s" % n)
        if any("DOCTYPE" in f for f in findings):
            return findings

    trees = {}
    for n, raw in blobs.items():
        if n.endswith((".xml", ".rels")) and any(r.match(n) for r in _ALLOW_RES):
            try:
                trees[n] = ET.fromstring(raw)
            except ET.ParseError as exc:
                findings.append("XML parse error in %s: %s" % (n, exc))

    ct = trees.get("[Content_Types].xml")
    if ct is not None:
        main_ok = False
        for el in ct.iter():
            kind = _local(el.tag)
            ctype = el.get("ContentType", "")
            if kind == "Default" and el.get("Extension", "").lower() == "bin":
                findings.append("content type default for .bin extension")
            if any(f in ctype.lower() for f in FORBIDDEN_CT):
                findings.append("forbidden content type: %s" % ctype)
            if kind == "Override" and el.get("PartName") == "/xl/workbook.xml":
                main_ok = ctype == MAIN_TYPE
                if not main_ok:
                    findings.append("workbook main content type not %s: %s" % (MAIN_TYPE, ctype))
        if not main_ok and not any("main content type" in f for f in findings):
            findings.append("workbook main content type override missing")

    for n in sorted(trees):
        if not n.endswith(".rels"):
            continue
        for el in trees[n].iter():
            if _local(el.tag) != "Relationship":
                continue
            rtype = el.get("Type", "")
            target = el.get("Target", "")
            if el.get("TargetMode") == "External":
                if not rtype.endswith("/hyperlink"):
                    findings.append("non-hyperlink external relationship in %s: %s" % (n, rtype))
                elif not host_allowed(target):
                    findings.append("hyperlink host not allowed in %s: %s" % (n, target))
                else:
                    u = urlsplit(target)
                    if u.username or u.password:
                        findings.append("hyperlink with userinfo in %s: %s" % (n, target))
            elif any(f in rtype.lower() for f in FORBIDDEN_REL):
                findings.append("forbidden internal relationship in %s: %s" % (n, rtype))

    wb = trees.get("xl/workbook.xml")
    if wb is not None:
        for el in wb.iter():
            tag = _local(el.tag)
            if tag in FORBIDDEN_WB_TAGS:
                findings.append("workbook contains %s" % tag)
            if tag == "sheet" and el.get("state") in ("hidden", "veryHidden"):
                findings.append("hidden sheet: %s" % el.get("name"))
            if tag == "definedName":
                t = (el.text or "")
                if "[" in t or "http" in t.lower() or "file:" in t.lower():
                    findings.append("definedName with external reference: %s" % el.get("name"))
                findings.extend(_formula_findings(
                    "xl/workbook.xml definedName %s" % el.get("name"), t))

    strings = []  # (origin, text)
    for n in sorted(trees):
        root = trees[n]
        if n == "xl/sharedStrings.xml":
            for si in root.iter():
                if _local(si.tag) == "si":
                    strings.append((n, _text(si)))
        elif re.match(r"^xl/worksheets/sheet\d+\.xml$", n):
            for el in root.iter():
                tag = _local(el.tag)
                if tag in FORBIDDEN_SHEET_TAGS:
                    findings.append("sheet %s contains %s" % (n, tag))
                elif tag == "hyperlink":
                    loc = el.get("location", "")
                    low = loc.lower()
                    if "[" in loc or "://" in low or "file:" in low or "\\" in loc:
                        findings.append("hyperlink location not allowed in %s: %s" % (n, loc[:60]))
                elif tag in FORMULA_TAGS:
                    findings.extend(_formula_findings(n, el.text or ""))
                elif tag == "is":
                    strings.append((n + " inline", _text(el)))
                elif tag == "c" and el.get("t") == "str":
                    for v in el:
                        if _local(v.tag) == "v":
                            strings.append((n + " cached", _unescape(v.text or "")))
        elif re.match(r"^xl/charts/chart\d+\.xml$", n):
            for el in root.iter():
                if _local(el.tag) == "f":
                    findings.extend(_formula_findings(n, el.text or ""))
    for origin, s in strings:
        if is_injection_string(s):
            findings.append("injection-style string in %s: %r" % (origin, s[:40]))
        # Same rule as CellWriter.text (WR-10): only newline among controls.
        if any((ord(c) < 32 and c != "\n") or ord(c) == 127 for c in s):
            findings.append("control character in string in %s: %r" % (origin, s[:40]))
    return findings


def _formula_findings(part, text):
    out = []
    if "[" in text:
        out.append("formula with external reference '[' in %s: %s" % (part, text[:60]))
    if "|" in text:
        out.append("formula with DDE '|' pattern in %s: %s" % (part, text[:60]))
    low = text.lower()
    if "://" in low or "file:" in low:
        out.append("formula with URL/file reference in %s: %s" % (part, text[:60]))
    if text.startswith("\\\\"):
        out.append("formula with UNC path in %s: %s" % (part, text[:60]))
    cleaned = text.upper().replace("_XLFN.", "").replace("_XLWS.", "")
    for m in sorted(set(_FUNC_RE.findall(cleaned))):
        out.append("formula uses banned function %s in %s" % (m, part))
    return out


def scan_or_raise(data):
    # type: (bytes) -> None
    findings = scan_xlsx_bytes(data)
    if findings:
        raise ScanError(findings)
