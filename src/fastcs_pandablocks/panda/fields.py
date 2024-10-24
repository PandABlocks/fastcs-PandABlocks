from __future__ import annotations

from enum import Enum

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import SubController
from fastcs.datatypes import Bool, Float, Int, String
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

from fastcs_pandablocks.handlers import UpdateEguSender
from fastcs_pandablocks.types.annotations import ResponseType


class WidgetGroup(Enum):
    """Purposely not an enum since we only ever want the string."""

    NONE = None
    PARAMETERS = "Parameters"
    OUTPUTS = "Outputs"
    INPUTS = "Inputs"
    READBACKS = "Readbacks"


class FieldController(SubController):
    def __init__(self):
        """
        Since fields contain an attribute for the field itself
        `PREFIX:BLOCK:FIELD`, but also subfields, `PREFIX:BLOCK:FIELD:SUB_FIELD`,
        have a top level attribute set in the `BlockController`, and
        further attributes which are used in the field as a `SubController`.
        """

        self.top_level_attribute: Attribute | None = None
        self._additional_attributes = {}
        super().__init__(search_device_for_attributes=False)

    @property
    def additional_attributes(self) -> dict[str, Attribute]:
        return self._additional_attributes

    def initialise(self):
        pass


class TableFieldController(FieldController):
    def __init__(self, table_field_info: TableFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            # To be added once we have a pvxs backend
            # description=table_field_info.description,
            group=WidgetGroup.OUTPUTS.value,
        )


class TimeFieldController(FieldController):
    def __init__(self, time_field_info: TimeFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Float(),
            # To be added once we have a pvxs backend
            # description=time_field_info.description,
            group=WidgetGroup.PARAMETERS.value,
        )
        self._additional_attributes["units"] = AttrW(
            String(),
            handler=UpdateEguSender(self.top_level_attribute),
            group=WidgetGroup.PARAMETERS.value,
        )


class TimeSubTypeParamFieldController(FieldController):
    def __init__(
        self,
        time_subtype_param_field_info: SubtypeTimeFieldInfo,
    ):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Float(),
            group=WidgetGroup.PARAMETERS.value,
        )


class TimeSubTypeReadFieldController(FieldController):
    def __init__(
        self,
        time_subtype_read_field_info: SubtypeTimeFieldInfo,
    ):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.READBACKS.value,
        )


class TimeSubTypeWriteFieldController(FieldController):
    def __init__(
        self,
        time_subtype_write_field_info: SubtypeTimeFieldInfo,
    ):
        super().__init__()
        self.top_level_attribute = AttrW(
            Float(),
            group=WidgetGroup.OUTPUTS.value,
        )


class BitOutFieldController(FieldController):
    def __init__(self, bit_out_field_info: BitOutFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.OUTPUTS.value,
        )


class PosOutFieldController(FieldController):
    def __init__(self, pos_out_field_info: PosOutFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.OUTPUTS.value,
        )


class ExtOutFieldController(FieldController):
    def __init__(self, ext_out_field_info: ExtOutFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.OUTPUTS.value,
        )


class ExtOutBitsFieldController(ExtOutFieldController):
    def __init__(
        self,
        ext_out_bits_field_info: ExtOutBitsFieldInfo,
    ):
        super().__init__(ext_out_bits_field_info)


class BitMuxFieldController(FieldController):
    def __init__(self, bit_mux_field_info: BitMuxFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.INPUTS.value,
        )


class PosMuxFieldController(FieldController):
    def __init__(self, pos_mux_field_info: PosMuxFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.INPUTS.value,
        )


class UintParamFieldController(FieldController):
    def __init__(self, uint_param_field_info: UintFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(prec=0),
            group=WidgetGroup.PARAMETERS.value,
        )


class UintReadFieldController(FieldController):
    def __init__(self, uint_read_field_info: UintFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(prec=0),
            group=WidgetGroup.READBACKS.value,
            # To be added once we have a pvxs backend
            # description=uint_read_field_info.description,
        )


class UintWriteFieldController(FieldController):
    def __init__(self, uint_write_field_info: UintFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrW(
            Float(prec=0),
            group=WidgetGroup.OUTPUTS.value,
        )


class IntParamFieldController(FieldController):
    def __init__(self, int_param_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Float(prec=0),
            group=WidgetGroup.PARAMETERS.value,
        )


class IntReadFieldController(FieldController):
    def __init__(self, int_read_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Int(),
            group=WidgetGroup.READBACKS.value,
        )


class IntWriteFieldController(FieldController):
    def __init__(self, int_write_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrW(
            Int(),
            group=WidgetGroup.PARAMETERS.value,
        )


class ScalarParamFieldController(FieldController):
    def __init__(self, scalar_param_field_info: ScalarFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Float(),
            group=WidgetGroup.PARAMETERS.value,
        )


class ScalarReadFieldController(FieldController):
    def __init__(self, scalar_read_field_info: ScalarFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.READBACKS.value,
        )


class ScalarWriteFieldController(FieldController):
    def __init__(self, scalar_write_field_info: ScalarFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.PARAMETERS.value,
        )


class BitParamFieldController(FieldController):
    def __init__(self, bit_param_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.PARAMETERS.value,
        )


class BitReadFieldController(FieldController):
    def __init__(self, bit_read_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.READBACKS.value,
        )


class BitWriteFieldController(FieldController):
    def __init__(self, bit_write_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.OUTPUTS.value,
        )


class ActionReadFieldController(FieldController):
    def __init__(self, action_read_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.READBACKS.value,
        )


class ActionWriteFieldController(FieldController):
    def __init__(self, action_write_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.OUTPUTS.value,
        )


class LutParamFieldController(FieldController):
    def __init__(self, lut_param_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.PARAMETERS.value,
        )


class LutReadFieldController(FieldController):
    def __init__(self, lut_read_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.READBACKS.value,
        )


class LutWriteFieldController(FieldController):
    def __init__(self, lut_read_field_info: FieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.OUTPUTS.value,
        )


class EnumParamFieldController(FieldController):
    def __init__(self, enum_param_field_info: EnumFieldInfo):
        super().__init__()
        self.allowed_values = enum_param_field_info.labels
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.PARAMETERS.value,
        )


class EnumReadFieldController(FieldController):
    def __init__(self, enum_read_field_info: EnumFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.READBACKS.value,
        )


class EnumWriteFieldController(FieldController):
    def __init__(self, enum_write_field_info: EnumFieldInfo):
        super().__init__()
        self.top_level_attribute = AttrW(
            String(),
            group=WidgetGroup.OUTPUTS.value,
        )


FieldControllerType = (
    TableFieldController
    | TimeFieldController
    | BitOutFieldController
    | PosOutFieldController
    | ExtOutFieldController
    | ExtOutBitsFieldController
    | BitMuxFieldController
    | PosMuxFieldController
    | UintParamFieldController
    | UintReadFieldController
    | UintWriteFieldController
    | IntParamFieldController
    | IntReadFieldController
    | IntWriteFieldController
    | ScalarParamFieldController
    | ScalarReadFieldController
    | ScalarWriteFieldController
    | BitParamFieldController
    | BitReadFieldController
    | BitWriteFieldController
    | ActionReadFieldController
    | ActionWriteFieldController
    | LutParamFieldController
    | LutReadFieldController
    | LutWriteFieldController
    | EnumParamFieldController
    | EnumReadFieldController
    | EnumWriteFieldController
    | TimeSubTypeParamFieldController
    | TimeSubTypeReadFieldController
    | TimeSubTypeWriteFieldController
)


def get_field_controller_from_field_info(
    field_info: ResponseType,
) -> FieldControllerType:
    match field_info:
        case TableFieldInfo():
            return TableFieldController(field_info)
        # Time types
        case TimeFieldInfo(subtype=None):
            return TimeFieldController(field_info)
        case SubtypeTimeFieldInfo(type="param"):
            return TimeSubTypeParamFieldController(field_info)
        case SubtypeTimeFieldInfo(subtype="read"):
            return TimeSubTypeReadFieldController(field_info)
        case SubtypeTimeFieldInfo(subtype="write"):
            return TimeSubTypeWriteFieldController(field_info)

        # Bit types
        case BitOutFieldInfo():
            return BitOutFieldController(field_info)
        case ExtOutBitsFieldInfo(subtype="timestamp"):
            return ExtOutFieldController(field_info)
        case ExtOutBitsFieldInfo():
            return ExtOutBitsFieldController(field_info)
        case ExtOutFieldInfo():
            return ExtOutFieldController(field_info)
        case BitMuxFieldInfo():
            return BitMuxFieldController(field_info)
        case FieldInfo(type="param", subtype="bit"):
            return BitParamFieldController(field_info)
        case FieldInfo(type="read", subtype="bit"):
            return BitReadFieldController(field_info)
        case FieldInfo(type="write", subtype="bit"):
            return BitWriteFieldController(field_info)

        # Pos types
        case PosOutFieldInfo():
            return PosOutFieldController(field_info)
        case PosMuxFieldInfo():
            return PosMuxFieldController(field_info)

        # Uint types
        case UintFieldInfo(type="param"):
            return UintParamFieldController(field_info)
        case UintFieldInfo(type="read"):
            return UintReadFieldController(field_info)
        case UintFieldInfo(type="write"):
            return UintWriteFieldController(field_info)

        # Scalar types
        case ScalarFieldInfo(subtype="param"):
            return ScalarParamFieldController(field_info)
        case ScalarFieldInfo(type="read"):
            return ScalarReadFieldController(field_info)
        case ScalarFieldInfo(type="write"):
            return ScalarWriteFieldController(field_info)

        # Int types
        case FieldInfo(type="param", subtype="int"):
            return IntParamFieldController(field_info)
        case FieldInfo(type="read", subtype="int"):
            return IntReadFieldController(field_info)
        case FieldInfo(type="write", subtype="int"):
            return IntWriteFieldController(field_info)

        # Action types
        case FieldInfo(
            type="read",
            subtype="action",
        ):
            return ActionReadFieldController(field_info)
        case FieldInfo(
            type="write",
            subtype="action",
        ):
            return ActionWriteFieldController(field_info)

        # Lut types
        case FieldInfo(type="param", subtype="lut"):
            return LutParamFieldController(field_info)
        case FieldInfo(type="read", subtype="lut"):
            return LutReadFieldController(field_info)
        case FieldInfo(type="write", subtype="lut"):
            return LutWriteFieldController(field_info)

        # Enum types
        case EnumFieldInfo(type="param"):
            return EnumParamFieldController(field_info)
        case EnumFieldInfo(type="read"):
            return EnumReadFieldController(field_info)
        case EnumFieldInfo(type="write"):
            return EnumWriteFieldController(field_info)

        case _:
            raise ValueError(f"Unknown field type: {type(field_info).__name__}.")
