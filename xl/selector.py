"""Selector state a workbook is built in (test-only override, T-03-24)."""
from checkmodel.measures_reference import DEFAULT_DIRECT_ETS, DEFAULT_STATE


def selector_state(dataset):
    """(basis, scenario), same order as DEFAULT_STATE; dataset field wins."""
    return getattr(dataset, "selector_state", None) or DEFAULT_STATE


def direct_ets_state(dataset):
    """Direct EU ETS1 toggle ("Off"/"On"); None field = deliverable default."""
    return getattr(dataset, "direct_ets_state", None) or DEFAULT_DIRECT_ETS
