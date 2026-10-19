"""Sources register aggregator over the seven section modules."""
from typing import Tuple

from config import (inputs_baseline, inputs_carbon, inputs_constants,
                    inputs_factors, inputs_finance, inputs_measures,
                    inputs_prices)
from config.schema import Source

SOURCES = (
    inputs_constants.SOURCES + inputs_baseline.SOURCES
    + inputs_prices.SOURCES + inputs_factors.SOURCES
    + inputs_carbon.SOURCES + inputs_finance.SOURCES
    + inputs_measures.SOURCES
)  # type: Tuple[Source, ...]
