from __future__ import annotations

from collections import namedtuple
from enum import Enum

from fastcs.attributes import AttrR, AttrRW, AttrW
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

from fastcs_pandablocks.types import AttrType, PandaName


class WidgetGroup(Enum):
    """Purposely not an enum since we only ever want the string."""

    NONE = None
    PARAMETERS = "Parameters"
    OUTPUTS = "Outputs"
    INPUTS = "Inputs"
    READBACKS = "Readbacks"


class NamedAttribute(namedtuple("NamedAttribute", "attribute_name attribute")):
    attribute_name: str
    attribute: AttrType


class SubFieldController(SubController):
    def __init__(self, attributes: list[NamedAttribute]):
        for attribute_name, attribute in attributes:
            setattr(self, attribute_name, attribute)


class Field:
    def __init__(
        self,
        attribute_name: str,
        attribute: AttrRW | AttrR | AttrW,
        sub_field_controller: SubFieldController | None = None,
    ):
        self.sub_field_controller = sub_field_controller

        self.block_attribute = (
            NamedAttribute(attribute_name=attribute_name, attribute=attribute)
            if (attribute_name and attribute)
            else None
        )


class TableField(Field):
    def __init__(self, panda_name: PandaName, table_field_info: TableFieldInfo):
        # TODO: Make a table type. For now we'll leave this to an int.
        table_field = AttrR(Float(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, table_field)


class TimeField(Field):
    def __init__(self, panda_name: PandaName, time_field_info: TimeFieldInfo):
        time_attr = AttrR(Float(), group=WidgetGroup.PARAMETERS.value)
        # TODO: Find out how to add EGU and such
        super().__init__(panda_name.attribute_name, time_attr)


class BitOutField(Field):
    def __init__(self, panda_name: PandaName, bit_out_field_info: BitOutFieldInfo):
        bit_out_attr = AttrRW(Bool(znam="0", onam="1"), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, bit_out_attr)


class PosOutField(Field):
    def __init__(self, panda_name: PandaName, pos_out_field_info: PosOutFieldInfo):
        # TODO add capture and dataset subfields
        pos_out_attr = AttrR(Float(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, pos_out_attr)


class ExtOutField(Field):
    def __init__(self, panda_name: PandaName, ext_out_field_info: ExtOutFieldInfo):
        # TODO add capture and dataset subfields
        ext_out_field = AttrR(Float(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, ext_out_field)


class ExtOutBitsField(ExtOutField):
    def __init__(
        self, panda_name: PandaName, ext_out_bits_field_info: ExtOutBitsFieldInfo
    ):
        # TODO add capture and dataset subfields
        super().__init__(panda_name, ext_out_bits_field_info)


class BitMuxField(Field):
    def __init__(self, panda_name: PandaName, bit_mux_field_info: BitMuxFieldInfo):
        bit_mux_attr = AttrRW(String(), group=WidgetGroup.INPUTS.value)
        super().__init__(panda_name.attribute_name, bit_mux_attr)


class PosMuxField(Field):
    def __init__(self, panda_name: PandaName, pos_mux_field_info: PosMuxFieldInfo):
        pos_mux_attr = AttrRW(String(), group=WidgetGroup.INPUTS.value)
        super().__init__(panda_name.attribute_name, pos_mux_attr)


class UintParamField(Field):
    def __init__(self, panda_name: PandaName, uint_param_field_info: UintFieldInfo):
        uint_param_attr = AttrR(Float(prec=0), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, uint_param_attr)


class UintReadField(Field):
    def __init__(self, panda_name: PandaName, uint_read_field_info: UintFieldInfo):
        uint_read_attr = AttrR(Float(prec=0), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, uint_read_attr)


class UintWriteField(Field):
    def __init__(self, panda_name: PandaName, uint_write_field_info: UintFieldInfo):
        uint_write_attr = AttrW(Float(prec=0), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, uint_write_attr)


class IntParamField(Field):
    def __init__(self, panda_name: PandaName, int_param_field_info: FieldInfo):
        uint_param_attr = AttrRW(Float(prec=0), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, uint_param_attr)


class IntReadField(Field):
    def __init__(self, panda_name: PandaName, int_read_field_info: FieldInfo):
        int_read_attr = AttrR(Int(), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, int_read_attr)


class IntWriteField(Field):
    def __init__(self, panda_name: PandaName, int_write_field_info: FieldInfo):
        int_write_attr = AttrW(Int(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, int_write_attr)


class ScalarParamField(Field):
    def __init__(self, panda_name: PandaName, scalar_param_field_info: ScalarFieldInfo):
        scalar_param_attr = AttrRW(Float(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, scalar_param_attr)


class ScalarReadField(Field):
    def __init__(self, panda_name: PandaName, scalar_read_field_info: ScalarFieldInfo):
        scalar_read_attr = AttrR(Float(), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, scalar_read_attr)


class ScalarWriteField(Field):
    def __init__(self, panda_name: PandaName, scalar_write_field_info: ScalarFieldInfo):
        scalar_read_attr = AttrR(Float(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, scalar_read_attr)


class BitParamField(Field):
    def __init__(self, panda_name: PandaName, bit_param_field_info: FieldInfo):
        bit_param_attr = AttrRW(
            Bool(znam="0", onam="1"), group=WidgetGroup.PARAMETERS.value
        )
        super().__init__(panda_name.attribute_name, bit_param_attr)


class BitReadField(Field):
    def __init__(self, panda_name: PandaName, bit_read_field_info: FieldInfo):
        bit_read_attr = AttrR(
            Bool(znam="0", onam="1"), group=WidgetGroup.READBACKS.value
        )
        super().__init__(panda_name.attribute_name, bit_read_attr)


class BitWriteField(Field):
    def __init__(self, panda_name: PandaName, bit_write_field_info: FieldInfo):
        bit_write_attr = AttrW(
            Bool(znam="0", onam="1"), group=WidgetGroup.OUTPUTS.value
        )
        super().__init__(panda_name.attribute_name, bit_write_attr)


class ActionReadField(Field):
    def __init__(self, panda_name: PandaName, action_read_field_info: FieldInfo):
        action_read_attr = AttrR(
            Bool(znam="0", onam="1"), group=WidgetGroup.READBACKS.value
        )
        super().__init__(panda_name.attribute_name, action_read_attr)


class ActionWriteField(Field):
    def __init__(self, panda_name: PandaName, action_write_field_info: FieldInfo):
        action_write_attr = AttrW(
            Bool(znam="0", onam="1"), group=WidgetGroup.OUTPUTS.value
        )
        super().__init__(panda_name.attribute_name, action_write_attr)


class LutParamField(Field):
    def __init__(self, panda_name: PandaName, lut_param_field_info: FieldInfo):
        lut_param_field = AttrRW(String(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, lut_param_field)


class LutReadField(Field):
    def __init__(self, panda_name: PandaName, lut_read_field_info: FieldInfo):
        lut_read_field = AttrR(String(), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, lut_read_field)


class LutWriteField(Field):
    def __init__(self, panda_name: PandaName, lut_read_field_info: FieldInfo):
        lut_write_field = AttrR(String(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, lut_write_field)


class EnumParamField(Field):
    def __init__(self, panda_name: PandaName, enum_param_field_info: EnumFieldInfo):
        self.allowed_values = enum_param_field_info.labels
        enum_param_field = AttrRW(String(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, enum_param_field)


class EnumReadField(Field):
    def __init__(self, panda_name: PandaName, enum_read_field_info: EnumFieldInfo):
        enum_read_field = AttrR(String(), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, enum_read_field)


class EnumWriteField(Field):
    def __init__(self, panda_name: PandaName, enum_write_field_info: EnumFieldInfo):
        enum_write_field = AttrW(String(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, enum_write_field)


class TimeSubTypeParamField(Field):
    def __init__(
        self, panda_name: PandaName, time_subtype_param_field_info: SubtypeTimeFieldInfo
    ):
        time_subtype_param_field = AttrRW(Float(), group=WidgetGroup.PARAMETERS.value)
        super().__init__(panda_name.attribute_name, time_subtype_param_field)


class TimeSubTypeReadField(Field):
    def __init__(
        self, panda_name: PandaName, time_subtype_read_field_info: SubtypeTimeFieldInfo
    ):
        time_subtype_read_field = AttrR(Float(), group=WidgetGroup.READBACKS.value)
        super().__init__(panda_name.attribute_name, time_subtype_read_field)


class TimeSubTypeWriteField(Field):
    def __init__(
        self, panda_name: PandaName, time_subtype_write_field_info: SubtypeTimeFieldInfo
    ):
        time_subtype_write_field = AttrW(Float(), group=WidgetGroup.OUTPUTS.value)
        super().__init__(panda_name.attribute_name, time_subtype_write_field)


FieldType = (
    TableField
    | TimeField
    | BitOutField
    | PosOutField
    | ExtOutField
    | ExtOutBitsField
    | BitMuxField
    | PosMuxField
    | UintParamField
    | UintReadField
    | UintWriteField
    | IntParamField
    | IntReadField
    | IntWriteField
    | ScalarParamField
    | ScalarReadField
    | ScalarWriteField
    | BitParamField
    | BitReadField
    | BitWriteField
    | ActionReadField
    | ActionWriteField
    | LutParamField
    | LutReadField
    | LutWriteField
    | EnumParamField
    | EnumReadField
    | EnumWriteField
    | TimeSubTypeParamField
    | TimeSubTypeReadField
    | TimeSubTypeWriteField
)

# TODO: Change to a match statement so we can easily add a PCAP field type.
FIELD_TYPE_TO_FASTCS_TYPE: dict[str, dict[str | None, type[FieldType]]] = {
    "table": {None: TableField},
    "time": {
        None: TimeField,
        "param": TimeSubTypeParamField,
        "read": TimeSubTypeReadField,
        "write": TimeSubTypeWriteField,
    },
    "bit_out": {
        None: BitOutField,
    },
    "pos_out": {
        None: PosOutField,
    },
    "ext_out": {
        "timestamp": ExtOutField,
        "samples": ExtOutField,
        "bits": ExtOutBitsField,
    },
    "bit_mux": {
        None: BitMuxField,
    },
    "pos_mux": {
        None: PosMuxField,
    },
    "param": {
        "uint": UintParamField,
        "int": IntParamField,
        "scalar": ScalarParamField,
        "bit": BitParamField,
        "action": ActionReadField,
        "lut": LutParamField,
        "enum": EnumParamField,
        "time": TimeSubTypeParamField,
    },
    "read": {
        "uint": UintReadField,
        "int": IntReadField,
        "scalar": ScalarReadField,
        "bit": BitReadField,
        "action": ActionReadField,
        "lut": LutReadField,
        "enum": EnumReadField,
        "time": TimeSubTypeReadField,
    },
    "write": {
        "uint": UintWriteField,
        "int": IntWriteField,
        "scalar": ScalarWriteField,
        "bit": BitWriteField,
        "action": ActionWriteField,
        "lut": LutWriteField,
        "enum": EnumWriteField,
        "time": TimeSubTypeWriteField,
    },
}
