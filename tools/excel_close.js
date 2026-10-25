// Best-effort cleanup helper (JXA): close, without saving, any open workbook
// named check.xlsx whose path contains the throwaway folder name passed as the
// only argument (Excel may report the path in POSIX or HFS form).
// Used by tools/excel_check.py after a failed or timed-out recalculation so
// no check workbook is left open in Excel. Never saves, never touches other
// workbooks.
function run(argv) {
  var folder = argv[0];
  var app = Application("Microsoft Excel");
  var books = app.workbooks();
  var closed = 0;
  for (var i = 0; i < books.length; i++) {
    var b = books[i], full = "", nm = "";
    try { nm = b.name(); full = String(b.fullName()); } catch (e) { continue; }
    if (nm === "check.xlsx" && full.indexOf(folder) !== -1) {
      try { b.close({saving: "no"}); closed++; } catch (e) {}
    }
  }
  return "closed " + closed;
}
