from __future__ import annotations

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Float, Int, String

from fastcs_pandablocks.types import EpicsName, PandaName, ResponseType

from .handler import FieldSender


class Field:
    def __init__(
        self,
        epics_name: EpicsName,
        panda_name: PandaName,
        description: str | None,
        datatype: Int | Float | String | Bool,
        attribute: type[AttrRW] | type[AttrR] | type[AttrW],
        sub_fields: dict[str, Field] | None = None,
    ):
        self.sub_fields = sub_fields or {}
        self.epics_name = epics_name
        self.panda_name = panda_name
        self.description = description

        self.datatype = datatype
        handler = FieldSender(panda_name) if attribute is AttrW else None
        if attribute is AttrW:
            self.attribute = attribute(datatype, handler=handler)
        else:
            self.attribute = attribute(datatype)

    async def update_value(self, sub_field: str | None, value: str):
        if sub_field:
            await self.sub_fields[sub_field].update_value(None, value)
        elif isinstance(self.attribute, AttrW):
            await self.attribute.process(value)
        else:
            await self.attribute.set(value)


class TableField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...


class TimeField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...


class BitOutField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class PosOutField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ExtOutField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ExtOutBitsField(ExtOutField):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class BitMuxField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class PosMuxField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class UintParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class UintReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class UintWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class IntParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class IntReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class IntWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ScalarParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ScalarReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ScalarWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class BitParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class BitReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class BitWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ActionReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class ActionWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class LutWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumParamField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumReadField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class EnumWriteField(Field):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeParamField(TimeField):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeReadField(TimeField):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
    ): ...

    ...


class TimeSubTypeWriteField(TimeField):
    def __init__(
        self, epics_name: EpicsName, panda_name: PandaName, description: str | None
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


class Block:
    _fields: dict[int | None, dict[str, FieldType]]

    def __init__(
        self,
        epics_name: EpicsName,
        number: int,
        description: str | None | None,
        raw_fields: dict[str, ResponseType],
    ):
        self.epics_name = epics_name
        self.number = number
        self.description = description
        self._fields = {}

        iterator = range(1, number + 1) if number > 1 else iter([None])

        for block_number in iterator:
            numbered_block_name = epics_name + EpicsName(block_number=block_number)
            self._fields[block_number] = {}

            for field_raw_name, field_info in raw_fields.items():
                field_epics_name = numbered_block_name + EpicsName(field=field_raw_name)
                field_panda_name = field_epics_name.to_panda_name()

                field = FIELD_TYPE_TO_FASTCS_TYPE[field_info.type][field_info.subtype](
                    field_epics_name, field_panda_name, field_info.description
                )
                self._fields[block_number][field_raw_name] = field

    async def update_field(self, panda_name: PandaName, value: str):
        assert panda_name.field
        await self._fields[panda_name.block_number][panda_name.field].update_value(
            panda_name.sub_field, value
        )
