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

ResponseType = (
    BitMuxFieldInfo
    | BitOutFieldInfo
    | EnumFieldInfo
    | ExtOutBitsFieldInfo
    | ExtOutFieldInfo
    | FieldInfo
    | PosMuxFieldInfo
    | PosOutFieldInfo
    | ScalarFieldInfo
    | SubtypeTimeFieldInfo
    | TableFieldInfo
    | TimeFieldInfo
    | UintFieldInfo
)
