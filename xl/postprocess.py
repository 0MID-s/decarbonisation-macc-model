"""Post-build patch: force a true date (time-scale) category axis on MACC charts.

Why this exists: the MACC technique A chart is an area chart on a date axis
whose "dates" are cumulative tCO2e, so the bars get variable widths. XlsxWriter
3.2.9 hard-codes ``<c:auto val="1"/>`` inside ``<c:dateAx>`` (Chart._write_date_axis
calls ``_write_auto(1)`` with no option to change it). With auto=1 Excel
decides the axis type itself and, for an area chart, picks a TEXT axis: equal
slots, trapezoids and a single "0" label. Excel confirmed (Excel for Mac 16.114)
that ``<c:auto val="0"/>`` (category type "Date axis" / time scale) renders the
intended variable-width rectangles; it is the value Excel itself writes.

The patch is stdlib only (zipfile). It rewrites the ``<c:auto>`` element only
inside ``<c:dateAx>...</c:dateAx>`` of ``xl/charts/chartN.xml`` parts, keeps
every other member byte-for-byte (same order, same compression type and date),
and fails loudly if the number of replacements is not the expected one.
It is idempotent: an already-patched file yields zero further replacements.
"""
import io
import re
import zipfile

_DATE_AX = re.compile(rb"<c:dateAx>.*?</c:dateAx>", re.S)
_CHART_PART = re.compile(r"^xl/charts/chart\d+\.xml$")
_AUTO_ON = b'<c:auto val="1"/>'
_AUTO_OFF = b'<c:auto val="0"/>'


class PostprocessError(ValueError):
    pass


def patch_date_axis(data, expected_charts):
    # type: (bytes, int) -> bytes
    """Return the workbook bytes with auto=0 on every dateAx.

    ``expected_charts`` is the number of chart parts that must contain a
    dateAx (the build knows this); anything else raises PostprocessError.
    """
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    found = 0
    with zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            raw = src.read(info.filename)
            if _CHART_PART.match(info.filename) and b"<c:dateAx>" in raw:
                found += 1

                def fix(m):
                    seg = m.group(0)
                    if seg.count(_AUTO_ON) + seg.count(_AUTO_OFF) != 1:
                        raise PostprocessError(
                            "%s: expected exactly one c:auto in dateAx"
                            % info.filename)
                    return seg.replace(_AUTO_ON, _AUTO_OFF)

                raw = _DATE_AX.sub(fix, raw)
                if b'<c:auto val="0"/>' not in raw:
                    raise PostprocessError(info.filename + ": patch failed")
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.comment = info.comment
            zi.extra = info.extra
            dst.writestr(zi, raw)
    if found != expected_charts:
        raise PostprocessError("expected %d chart(s) with a date axis, found %d"
                               % (expected_charts, found))
    return out.getvalue()
