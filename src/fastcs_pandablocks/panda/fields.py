from __future__ import annotations

from typing import Literal

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import SubController
from fastcs.datatypes import Bool, Float, Int, String

from fastcs_pandablocks.types import PandaName


class PviGroup:
    """Purposely not an enum since we only ever want the string."""
    PARAMETERS = "Parameters"
    OUTPUTS = "Outputs"
    INPUTS = "Inputs"
    READBACKS = "Readbacks"

PviGroupField = Literal["Parameters", "Outputs", "Inputs", "Readbacks"]


class Field(SubController):
    def __init__(
        self,
        attribute_name: str | None,
        attribute: AttrRW | AttrR | AttrW | None,
        sub_fields: dict[str, FieldType] | None = None,
    ):
        """
        For controlling the field, sub fields can also be added.
        attribute_name and attribute are optional since some fields
        e.g won't contain a top level record, but only sub fields.
        """
        super().__init__()
        self.sub_fields = sub_fields or {}
        self.attribute_name = attribute_name

        if attribute_name and attribute:
            setattr(self, attribute_name, attribute)

        for sub_field_name, sub_field in self.sub_fields.items():
            self.register_sub_controller(
                PandaName(sub_field=sub_field_name).attribute_name,
                sub_field
            )

    async def update_value(self, value: str):
        if self.attribute_name is None:
            return

        attribute = getattr(self, self.attribute_name)
        if isinstance(attribute, AttrW):
            await attribute.process(value)
        else:
            await attribute.set(value)


class TableField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...


class TimeField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):

        time_attr = AttrR(Float(), group=PviGroup.PARAMETERS)
        # TODO: Find out how to add EGU and such
        super().__init__(panda_name.attribute_name, time_attr)


class BitOutField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        bit_out_attr = AttrRW(Bool(znam="0", onam="1"), group=PviGroup.OUTPUTS)
        super().__init__(panda_name.attribute_name, bit_out_attr)


class PosOutField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        # TODO add capture and dataset subfields
        pos_out_attr = AttrR(Float(), group=PviGroup.OUTPUTS)
        super().__init__(panda_name.attribute_name, pos_out_attr)


class ExtOutField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        # TODO add capture and dataset subfields
        super().__init__(None, None)


class ExtOutBitsField(ExtOutField):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        # TODO add capture and dataset subfields
        super().__init__(panda_name, description)


class BitMuxField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        bit_mux_attr = AttrRW(String(), group=PviGroup.INPUTS)
        super().__init__(panda_name.attribute_name, bit_mux_attr)


class PosMuxField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        pos_mux_attr = AttrRW(String(), group=PviGroup.INPUTS)
        super().__init__(panda_name.attribute_name, pos_mux_attr)

class UintParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        uint_param_attr = AttrR(Float(prec=0), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, uint_param_attr)

class UintReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        uint_read_attr = AttrR(Float(prec=0), group=PviGroup.READBACKS)
        super().__init__(panda_name.attribute_name, uint_read_attr)


class UintWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        uint_write_attr = AttrW(Float(prec=0), group=PviGroup.OUTPUTS)
        super().__init__(panda_name.attribute_name, uint_write_attr)


class IntParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        uint_param_attr = AttrRW(Float(prec=0), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, uint_param_attr)


class IntReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        int_read_attr = AttrR(Int(), group=PviGroup.READBACKS)
        super().__init__(panda_name.attribute_name, int_read_attr)


class IntWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        int_write_attr = AttrW(Int(), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, int_write_attr)


class ScalarParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        scalar_param_attr = AttrRW(Float(), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, scalar_param_attr)


class ScalarReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        scalar_read_attr = AttrR(Float(), group=PviGroup.READBACKS)
        super().__init__(panda_name.attribute_name, scalar_read_attr)

class ScalarWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        scalar_read_attr = AttrR(Float(), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, scalar_read_attr)


class BitParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        bit_param_attr = AttrRW(Bool(znam="0", onam="1"), group=PviGroup.PARAMETERS)
        super().__init__(panda_name.attribute_name, bit_param_attr)


class BitReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        bit_read_attr = AttrR(Bool(znam="0", onam="1"), group=PviGroup.READBACKS)
        super().__init__(panda_name.attribute_name, bit_read_attr)

class BitWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        bit_write_attr = AttrW(Bool(znam="0", onam="1"), group=PviGroup.OUTPUTS)
        super().__init__(panda_name.attribute_name, bit_write_attr)


class ActionReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ):
        action_read_attr = AttrW(Bool(znam="0", onam="1"), group=PviGroup.READBACKS)
        super().__init__(panda_name.attribute_name, action_read_attr)


class ActionWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumParamField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumReadField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumWriteField(Field):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeParamField(TimeField):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeReadField(TimeField):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeWriteField(TimeField):
    def __init__(
        self, panda_name: PandaName, description: str | None
    ): ...

    ...


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
