// Excel desktop recalculation helper (JXA). Run with:
//   osascript -l JavaScript tools/excel_recalc.js <workbook> <cells.json> <out.json> <scenario> <basis> <direct_ets> <scen_cell> <basis_cell> <ets_cell>
// It addresses Microsoft Excel only, opens the throwaway copy, sets
// the three selector cells (addresses passed as arguments), runs a full
// recalculation, writes the value of every listed formula cell to out.json
// and closes the workbook without saving. Numeric values are read as numbers,
// never as displayed text (the Mac locale uses a decimal comma).
ObjC.import("Foundation");

function readText(path) {
  var s = $.NSString.stringWithContentsOfFileEncodingError($(path), $.NSUTF8StringEncoding, null);
  return ObjC.unwrap(s);
}

function writeText(path, text) {
  $(text).writeToFileAtomicallyEncodingError($(path), true, $.NSUTF8StringEncoding, null);
}

function colLetters(n) {
  var s = "";
  while (n > 0) { var m = (n - 1) % 26; s = String.fromCharCode(65 + m) + s; n = Math.floor((n - 1) / 26); }
  return s;
}

// Find the workbook we just opened: never trust the active workbook, which could be
// the user's own workbook if the open is deferred or blocked.
function findOpened(app, wbPath) {
  var wanted = wbPath.split("/").pop();
  var parent = wbPath.split("/").slice(-2, -1)[0];
  var books = app.workbooks();
  for (var i = 0; i < books.length; i++) {
    var b = books[i], nm = "", full = "";
    try { nm = b.name(); full = String(b.fullName()); } catch (e) { continue; }
    if (nm === wanted && full.indexOf(parent) !== -1) { return b; }
  }
  return null;
}

function run(argv) {
  var wbPath = argv[0], cellsPath = argv[1], outPath = argv[2];
  var scenario = argv[3], basis = argv[4], directEts = argv[5];
  // selector cell addresses on the Inputs sheet, resolved from the workbook's
  // defined names by tools/excel_check.py (Sel_Scenario, Sel_Basis, Sel_DirectETS)
  var scenCell = argv[6], basisCell = argv[7], etsCell = argv[8];
  var spec = JSON.parse(readText(cellsPath));  // {sheet: {"maxrow": n, "maxcol": n, "cells": [[r, c], ...]}}
  var app = Application("Microsoft Excel");
  var alertsBefore = app.displayAlerts();
  app.displayAlerts = false;
  var wb = null;
  try {
    app.open(Path(wbPath));
    wb = findOpened(app, wbPath);
    if (wb === null) { throw new Error("opened workbook not found: " + wbPath); }
    var inputs = wb.worksheets.byName("Inputs");
    inputs.cells.byName(scenCell).value = scenario;
    inputs.cells.byName(basisCell).value = basis;
    inputs.cells.byName(etsCell).value = directEts;
    app.calculateFull();
    var out = {};
    var sheets = Object.keys(spec);
    for (var i = 0; i < sheets.length; i++) {
      var name = sheets[i], info = spec[name];
      var ws = wb.worksheets.byName(name);
      var rng = ws.cells.byName("A1:" + colLetters(info.maxcol) + info.maxrow);
      var vals = rng.value();
      // a 1x1 range returns a scalar, not a 2-D array
      if (!Array.isArray(vals)) { vals = [[vals]]; }
      for (var k = 0; k < info.cells.length; k++) {
        var r = info.cells[k][0], c = info.cells[k][1];
        var v = vals[r - 1][c - 1];
        out[name + "!" + colLetters(c) + r] = v;
      }
    }
    writeText(outPath, JSON.stringify(out));
    return "ok " + Object.keys(out).length;
  } finally {
    if (wb !== null) { try { wb.close({saving: "no"}); } catch (e) {} }
    try { app.displayAlerts = alertsBefore; } catch (e) {}
  }
}
