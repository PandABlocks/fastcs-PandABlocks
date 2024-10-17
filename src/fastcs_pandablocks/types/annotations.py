from fastcs.attributes import AttrR, AttrRW, AttrW
from typing import Union
from pandablocks.responses import (
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
)


# Pyright gives us variable not allowed in type expression error
# if we try to use the new (|) syntax
ResponseType = Union[
    BitMuxFieldInfo,
    BitOutFieldInfo,
     EnumFieldInfo
    , ExtOutBitsFieldInfo
    , ExtOutFieldInfo
    , FieldInfo
    , PosMuxFieldInfo
    , PosOutFieldInfo
    , ScalarFieldInfo
    , SubtypeTimeFieldInfo
    , TableFieldInfo
    , TimeFieldInfo
    , UintFieldInfo
]


AttrType = Union[AttrRW, AttrR, AttrW]
