from .missing_output_format import MissingOutputFormatRule
from .no_output_limit import NoOutputLimitRule

CORE_RULES = [
    MissingOutputFormatRule(),
    NoOutputLimitRule(),
]