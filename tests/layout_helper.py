"""Test helper: build the real workbook in memory and return the layouts dict."""
import io

import xlsxwriter

import build
from config.build_config import BUILD
from xl.cells import CellWriter
from xl.styles import Styles


def build_layouts():
    ds = build.load_dataset("config")
    wb = xlsxwriter.Workbook(io.BytesIO(), build.OPTIONS)
    layouts = build._build_main(wb, Styles(wb), CellWriter(wb), ds, BUILD)
    wb.close()
    return layouts
