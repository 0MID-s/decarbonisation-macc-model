"""Input register aggregator over the seven section modules."""
from typing import Tuple

from config import (inputs_baseline, inputs_carbon, inputs_constants,
                    inputs_factors, inputs_finance, inputs_measures,
                    inputs_prices)
from config.schema import InputRecord

INPUTS = (
    inputs_constants.INPUTS + inputs_baseline.INPUTS + inputs_prices.INPUTS
    + inputs_factors.INPUTS + inputs_carbon.INPUTS + inputs_finance.INPUTS
    + inputs_measures.INPUTS
)  # type: Tuple[InputRecord, ...]
