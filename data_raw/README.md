# data_raw/ : untrusted downloads

- Everything in this folder is untrusted data. Nothing here is executed, imported or opened in Excel.
- One subdirectory per source ID.
- Files are fetched only through `tools/fetch_raw.py` (built in plan 01-04) from allowlisted official domains.
- Parsing scripts live outside `data_raw/` and run with `python3 -I`, reading files as data only.
- Never open a downloaded workbook in Excel and never enable macros.
- Folder contents are gitignored; only this README is tracked.
