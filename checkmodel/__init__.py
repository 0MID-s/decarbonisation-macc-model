"""Independent reference model: pure Python, stdlib only.

Re-implements workbook logic so cached values and tests do not depend on the
workbook code. Never imports xl/ or tests; all data arrives as arguments.
"""
