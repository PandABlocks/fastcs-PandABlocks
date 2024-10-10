import itertools
from pprint import pprint
from typing import Type
from fastcs_pandablocks.types import EpicsName, PandaName, ResponseType

panda_name_to_field = {}

class Field:
    def __init__(self, epics_name: EpicsName, panda_name: PandaName, field_info: ResponseType):
        self.epics_name = epics_name
        self.panda_name = panda_name
        self.field_info = field_info
        self.value = None
        panda_name_to_field[panda_name] = self

    def update_value(self, value):
        self.value = value

class TableField(Field):
    ...

class TimeField(Field):
    ...

class BitOutField(Field):
    ...

class PosOutField(Field):
    ...

class ExtOutField(Field):
    ...

class ExtOutBitsField(ExtOutField):
    ...

class BitMuxField(Field):
    ...

class PosMuxField(Field):
    ...

class UintParamField(Field):
    ...

class UintReadField(Field):
    ...

class UintWriteField(Field):
    ...

class IntParamField(Field):
    ...

class IntReadField(Field):
    ...

class IntWriteField(Field):
    ...

class ScalarParamField(Field):
    ...

class ScalarReadField(Field):
    ...

class ScalarWriteField(Field):
    ...

class BitParamField(Field):
    ...

class BitReadField(Field):
    ...

class BitWriteField(Field):
    ...

class ActionReadField(Field):
    ...

class ActionWriteField(Field):
    ...

class LutParamField(Field):
    ...

class LutReadField(Field):
    ...

class LutWriteField(Field):
    ...

class EnumParamField(Field):
    ...

class EnumReadField(Field):
    ...

class EnumWriteField(Field):
    ...

class TimeSubTypeParamField(TimeField):
    ...

class TimeSubTypeReadField(TimeField):
    ...

class TimeSubTypeWriteField(TimeField):
    ...

FieldType = (
    TableField |
    TimeField |
    BitOutField |
    PosOutField |
    ExtOutField |
    ExtOutBitsField |
    BitMuxField |
    PosMuxField |
    UintParamField |
    UintReadField |
    UintWriteField |
    IntParamField |
    IntReadField |
    IntWriteField |
    ScalarParamField |
    ScalarReadField |
    ScalarWriteField |
    BitParamField |
    BitReadField |
    BitWriteField |
    ActionReadField |
    ActionWriteField |
    LutParamField |
    LutReadField |
    LutWriteField |
    EnumParamField |
    EnumReadField |
    EnumWriteField |
    TimeSubTypeParamField |
    TimeSubTypeReadField |
    TimeSubTypeWriteField
)

FIELD_TYPE_TO_FASTCS_TYPE: dict[str, dict[str | None, Type[FieldType]]] = {
    "table": {
        None: TableField
    },
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
        description: str | None,
        raw_fields: dict[str, ResponseType]
    ):
        self.epics_name = epics_name
        self.number = number
        self.description = description
        self._fields = {}

        for number in range(1, number + 1):
            numbered_block_name = epics_name + EpicsName(block_number=number)
            self._fields[number] = {}

            for field_raw_name, field_info in (
                raw_fields.items()
            ):
                field_epics_name_without_block = field_panda_name.to_epics_name()
                print("part", field_epics_name_without_block)
                field_epics_name = (
                    numbered_block_name + field_epics_name_without_block
                )
                print("WHOE", field_epics_name)
                field = FIELD_TYPE_TO_FASTCS_TYPE[field_info.type][field_info.subtype](
                    field_epics_name, field_panda_name, field_info
                )
                self._fields[number][field_name] = field

    def update_value(self, number: int | None, field_name: str, value):
        self._fields[number][field_name].update_value(value)
