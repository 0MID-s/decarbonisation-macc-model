"""RowWriter: row-level writing helper shared by sheets after Measures.

Same behaviour as the private writer in xl/sheets/measures.py (kept unchanged),
but the sheet name and column constants are parameters, so Carbon and Exposure
can reuse it.
"""
from xl.layout import (
    LABEL_COL, TIMELINE_FIRST_COL, TIMELINE_LAST_COL, UNIT_COL, col_letter)

NYEARS_DEFAULT = TIMELINE_LAST_COL - TIMELINE_FIRST_COL + 1


class RowWriter(object):
    def __init__(self, ws, cells, styles, sheet, last_col, scalar_col=3,
                 note_col=None, nyears=NYEARS_DEFAULT):
        self.ws, self.cells, self.styles = ws, cells, styles
        self.sheet, self.last_col = sheet, last_col
        self.scalar_col = scalar_col
        self.note_col = scalar_col + 1 if note_col is None else note_col
        self.nyears = nyears

    def band(self, r, title):
        sec = self.styles.get("section")
        self.cells.text(self.ws, r, LABEL_COL, title, sec)
        for c in range(LABEL_COL + 1, self.last_col + 1):
            self.cells.blank(self.ws, r, c, sec)

    def line(self, r, text, unit=""):
        self.cells.text(self.ws, r, LABEL_COL, text, self.styles.get("label"))
        if unit:
            self.cells.text(self.ws, r, UNIT_COL, unit,
                            self.styles.get("unit"))

    def note(self, r, text, col=None):
        self.cells.text(self.ws, r, self.note_col if col is None else col,
                        text, self.styles.get("note"))

    def scalar(self, r, f, value, num, link=False, name=None):
        role = "link" if link else "calc"
        self.cells.formula(self.ws, r, self.scalar_col, f,
                           self.styles.get(role, num), value=value)
        if name:
            cells = self.cells
            cells.define_name(name, "=%s!$%s$%d" % (
                self.sheet, col_letter(self.scalar_col), r + 1))

    def series(self, r, fn, values, num, link=False, name=None, tag=None):
        role = "link" if link else "calc"
        fmt = self.styles.get(role, num)
        for k in range(self.nyears):
            cl = col_letter(TIMELINE_FIRST_COL + k)
            self.cells.formula(self.ws, r, TIMELINE_FIRST_COL + k,
                               fn(k, cl), fmt, value=values[k])
        if name:
            cells = self.cells
            cells.define_name(name, "=%s!$%s$%d:$%s$%d" % (
                self.sheet, col_letter(TIMELINE_FIRST_COL), r + 1,
                col_letter(TIMELINE_FIRST_COL + self.nyears - 1), r + 1))
            if tag:
                cells.tag_name(name, tag)
