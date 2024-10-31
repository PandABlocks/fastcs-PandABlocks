from typing import Union

from pandablocks.responses import (
    BitMuxFieldInfo,
    BitOutFieldInfo,
    BlockInfo,
    EnumFieldInfo,
    ExtOutBitsFieldInfo,
    ExtOutFieldInfo,
    FieldInfo,
    PosMuxFieldInfo,
    PosOutFieldInfo,
    ScalarFieldInfo,
    SubtypeTimeFieldInfo,
    TableFieldInfo,
    TimeFieldInfo,
    UintFieldInfo,
)

from .string_types import PandaName

# Pyright gives us variable not allowed in type expression error
# if we try to use the new (|) syntax
ResponseType = Union[
    BitMuxFieldInfo,
    BitOutFieldInfo,
    EnumFieldInfo,
    ExtOutBitsFieldInfo,
    ExtOutFieldInfo,
    FieldInfo,
    PosMuxFieldInfo,
    PosOutFieldInfo,
    ScalarFieldInfo,
    SubtypeTimeFieldInfo,
    TableFieldInfo,
    TimeFieldInfo,
    UintFieldInfo,
]

RawBlocksType = dict[PandaName, BlockInfo]
RawFieldsType = list[dict[PandaName, ResponseType]]
RawInitialValuesType = dict[PandaName, str]
