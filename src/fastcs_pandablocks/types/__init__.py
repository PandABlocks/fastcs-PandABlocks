from enum import Enum

from ._annotations import (
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
    ResponseType,
)
from ._string_types import (
    PANDA_SEPARATOR,
    PandaName,
)


class WidgetGroup(Enum):
    NONE = None
    PARAMETERS = "Parameters"
    OUTPUTS = "Outputs"
    INPUTS = "Inputs"
    READBACKS = "Readbacks"
    CAPTURE = "Capture"


__all__ = [
    "PANDA_SEPARATOR",
    "PandaName",
    "ResponseType",
    "RawBlocksType",
    "RawFieldsType",
    "RawInitialValuesType",
    "WidgetGroup",
]
