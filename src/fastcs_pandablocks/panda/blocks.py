import itertools
from pprint import pprint
from typing import Type
from fastcs_pandablocks.types import EpicsName, ResponseType

class Field:
        def __init__(self, name: EpicsName, field_info: ResponseType):
                self.name = name
                self.field_info = field_info

def change_value(self, new_field_value):
        print("setting value", new_field_value)
        self.value = new_field_value

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

class BitWriteField(Field):
        ...

class BitReadField(Field):
        ...

class ActionWriteField(Field):
        ...

class ActionReadField(Field):
        ...

class LutParamField(Field):
        ...

class LutWriteField(Field):
        ...

class LutReadField(Field):
        ...

class EnumParamField(Field):
        ...

class EnumWriteField(Field):
        ...

class EnumReadField(Field):
        ...

class TimeSubTypeParamField(Field):
        ...

class TimeSubTypeReadField(Field):
        ...

class TimeSubTypeWriteField(Field):
        ...

FieldType = (
    TableField
    | BitParamField
    | BitWriteField
    | BitReadField
    | ActionWriteField
    | ActionReadField
    | LutParamField
    | LutWriteField
    | LutReadField
    | EnumParamField
    | EnumWriteField
    | EnumReadField
    | TimeSubTypeParamField
    | TimeSubTypeReadField
    | TimeSubTypeWriteField
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
    _sub_blocks: dict[int, dict[EpicsName, FieldType]]

    def __init__(self, name: EpicsName, number: int, description: str | None, raw_fields: dict[str, ResponseType]):
        self.name = name
        self.number = number
        self.description = description
        self._sub_blocks = {}

        for number in range(1, number + 1):
            numbered_block = name + EpicsName(str(number))
            single_block = self._sub_blocks[number] = {}

            for field_suffix, field_info in (
                raw_fields.items()
            ):
                field_name = (
                       numbered_block + EpicsName(field_suffix)
                )
                single_block[EpicsName(field_suffix)] = (
                    FIELD_TYPE_TO_FASTCS_TYPE[field_info.type][field_info.subtype](
                        field_name, field_info
                    )
                )
    def change_value(self, new_field_value, block_number, field_name):
        self._sub_blocks[block_number][field_name].change_value(new_field_value)
