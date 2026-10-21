"""Selector state a workbook is built in (test-only override, T-03-24)."""
from checkmodel.measures_reference import DEFAULT_STATE


def selector_state(dataset):
    """(basis, scenario), same order as DEFAULT_STATE; dataset field wins."""
    return getattr(dataset, "selector_state", None) or DEFAULT_STATE
