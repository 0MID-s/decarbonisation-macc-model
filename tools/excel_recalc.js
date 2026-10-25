// Excel desktop recalculation helper (JXA). Run with:
//   osascript -l JavaScript tools/excel_recalc.js <workbook> <cells.json> <out.json> <scenario> <basis> <direct_ets>
// It addresses Microsoft Excel only, opens the throwaway copy, sets
// Inputs!G8 (scenario), G9 (basis) and G10 (direct ETS Off/On), runs a full
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

function run(argv) {
  var wbPath = argv[0], cellsPath = argv[1], outPath = argv[2];
  var scenario = argv[3], basis = argv[4], directEts = argv[5];
  var spec = JSON.parse(readText(cellsPath));  // {sheet: {"maxrow": n, "maxcol": n, "cells": [[r, c], ...]}}
  var app = Application("Microsoft Excel");
  app.displayAlerts = false;
  app.open(Path(wbPath));
  var wb = app.activeWorkbook;
  var inputs = wb.worksheets.byName("Inputs");
  inputs.cells.byName("G8").value = scenario;
  inputs.cells.byName("G9").value = basis;
  inputs.cells.byName("G10").value = directEts;
  app.calculateFull();
  var out = {};
  var sheets = Object.keys(spec);
  for (var i = 0; i < sheets.length; i++) {
    var name = sheets[i], info = spec[name];
    var ws = wb.worksheets.byName(name);
    var rng = ws.cells.byName("A1:" + colLetters(info.maxcol) + info.maxrow);
    var vals = rng.value();
    for (var k = 0; k < info.cells.length; k++) {
      var r = info.cells[k][0], c = info.cells[k][1];
      var v = vals[r - 1][c - 1];
      out[name + "!" + colLetters(c) + r] = v;
    }
  }
  wb.close({saving: "no"});
  writeText(outPath, JSON.stringify(out));
  return "ok " + Object.keys(out).length;
}
