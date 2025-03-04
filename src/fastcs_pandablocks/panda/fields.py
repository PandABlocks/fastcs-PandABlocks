from __future__ import annotations

import enum

import numpy as np
from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.datatypes import Bool, Enum, Float, Int, String, Table
from numpy.typing import DTypeLike
from pandablocks.commands import TableFieldDetails
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

from fastcs_pandablocks.handlers import (
    CaptureHandler,
    DatasetHandler,
    DefaultFieldHandler,
    DefaultFieldSender,
    DefaultFieldUpdater,
    EguSender,
    TableFieldHandler,
)
from fastcs_pandablocks.types import (
    PandaName,
    RawInitialValuesType,
    ResponseType,
    WidgetGroup,
)


def make_attributes(
    block_panda_name: PandaName,
    field_infos: dict[PandaName, ResponseType],
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes = {}
    for field_panda_name, field_info in field_infos.items():
        full_field_name = block_panda_name + field_panda_name
        field_initial_values = {
            key: value
            for key, value in initial_values.items()
            if key in field_panda_name
        }
        attributes.update(
            get_field_controller_from_field_info(
                full_field_name, field_info, field_initial_values
            )
        )
    return attributes


def _table_datatypes_from_table_field_details(
    details: TableFieldDetails,
) -> DTypeLike:
    match details:
        case TableFieldDetails(subtype="int"):
            return np.int32
        case TableFieldDetails(subtype="uint"):
            return np.uint32
        case TableFieldDetails(subtype="enum"):
            # TODO: replace with string once
            # https://github.com/epics-base/p4p/issues/168
            # is fixed.
            return np.uint32
        case _:
            raise RuntimeError("Received unknown datatype for table in panda.")


def make_table_field_attributes(
    panda_name: PandaName,
    field_info: TableFieldInfo,
) -> dict[PandaName, Attribute]:
    structured_datatype = [
        (name, _table_datatypes_from_table_field_details(details))
        for name, details in field_info.fields.items()
    ]

    return {
        panda_name: AttrRW(
            Table(structured_datatype),
            handler=TableFieldHandler(panda_name),
        )
    }


def make_time_param_attributes(
    panda_name: PandaName,
    field_info: SubtypeTimeFieldInfo | TimeFieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    units_enum = enum.Enum("Units", field_info.units_labels)
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        Float(),
        handler=DefaultFieldHandler(panda_name),
        description=field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=float(initial_values[panda_name]),
    )
    attributes[panda_name + PandaName(sub_field="units")] = AttrW(
        Enum(units_enum),
        handler=EguSender(attributes[panda_name]),
        group=WidgetGroup.PARAMETERS.value,
    )
    return attributes


def make_time_read_attributes(
    panda_name: PandaName,
    field_info: SubtypeTimeFieldInfo,
    initial_values: RawInitialValuesType,
):
    units_enum = enum.Enum("Units", field_info.units_labels)
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Float(),
        handler=DefaultFieldUpdater(
            panda_name=panda_name,
        ),
        description=field_info.description,
        group=WidgetGroup.OUTPUTS.value,
        initial_value=float(initial_values[panda_name]),
    )
    attributes[panda_name + PandaName(sub_field="units")] = AttrW(
        Enum(units_enum),
        handler=EguSender(attributes[panda_name]),
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def make_time_write_attributes(
    panda_name: PandaName,
    field_info: SubtypeTimeFieldInfo,
):
    units_enum = enum.Enum("Units", field_info.units_labels)
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrW(
        Float(),
        handler=DefaultFieldSender(panda_name),
        description=field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    attributes[panda_name + PandaName(sub_field="units")] = AttrW(
        Enum(units_enum),
        handler=EguSender(attributes[panda_name]),
        group=WidgetGroup.READBACKS.value,
    )
    return attributes


def make_bit_out_attributes(
    panda_name: PandaName,
    field_info: BitOutFieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    return {
        panda_name: AttrR(
            Bool(),
            description=field_info.description,
            group=WidgetGroup.OUTPUTS.value,
            initial_value=bool(int(initial_values[panda_name])),
        )
    }


def make_pos_out_attributes(
    panda_name: PandaName,
    field_info: PosOutFieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    pos_out = AttrR(
        Bool(),
        description=field_info.description,
        group=WidgetGroup.OUTPUTS.value,
        initial_value=bool(int(initial_values[panda_name])),
    )
    attributes[panda_name] = pos_out

    scaled = AttrR(
        Float(),
        group=WidgetGroup.CAPTURE.value,
        description="Value with scaling applied.",
    )

    scale = AttrRW(
        Float(),
        group=WidgetGroup.CAPTURE.value,
        handler=DefaultFieldHandler(panda_name),
    )
    offset = AttrRW(
        Float(),
        group=WidgetGroup.CAPTURE.value,
        handler=DefaultFieldHandler(panda_name),
    )

    async def updated_scaled_on_offset_change(*_):
        await scaled.set(scale.get() * pos_out.get() + offset.get())

    offset.set_update_callback(updated_scaled_on_offset_change)

    attributes[panda_name + PandaName(sub_field="scaled")] = scaled
    attributes.update(
        {
            panda_name + PandaName(sub_field="scaled"): scaled,
            panda_name + PandaName(sub_field="scale"): scale,
            panda_name + PandaName(sub_field="offset"): offset,
        }
    )

    attributes[panda_name + PandaName(sub_field="capture")] = AttrRW(
        Enum(enum.Enum("Capture", field_info.capture_labels)),
        group=WidgetGroup.CAPTURE.value,
        handler=CaptureHandler(),
    )
    attributes[panda_name + PandaName(sub_field="dataset")] = AttrRW(
        Enum(enum.Enum("Dataset", field_info.capture_labels)),
        group=WidgetGroup.CAPTURE.value,
        handler=DatasetHandler(),
    )
    return attributes


def make_ext_out_attributes(
    panda_name: PandaName,
    field_info: ExtOutFieldInfo,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Float(),
        description=field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    attributes[panda_name + PandaName(sub_field="capture")] = AttrRW(
        Enum(enum.Enum("Capture", field_info.capture_labels)),
        group=WidgetGroup.CAPTURE.value,
        handler=CaptureHandler(),
    )
    attributes[panda_name + PandaName(sub_field="dataset")] = AttrRW(
        Enum(enum.Enum("Dataset", field_info.capture_labels)),
        group=WidgetGroup.CAPTURE.value,
        handler=DatasetHandler(),
    )
    return attributes


def make_bits_sub_field_attributes(
    panda_name: PandaName, label: str
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Bool(),
        description="Value of the field connected to this bit.",
        group=WidgetGroup.OUTPUTS.value,
    )
    attributes[panda_name + PandaName(sub_field="name")] = AttrR(
        String(),
        description="Name of the field connected to this bit.",
        initial_value=label,
    )
    return attributes


def make_ext_out_bits_attributes(
    panda_name: PandaName,
    field_info: ExtOutBitsFieldInfo,
):
    attributes = make_ext_out_attributes(panda_name, field_info)

    for bit_number, label in enumerate(field_info.bits, start=1):
        if label == "":
            continue  # Some rows are empty, do not create records.

        sub_field_panda_name = panda_name + PandaName(sub_field=f"bit{bit_number}")
        attributes[sub_field_panda_name] = AttrR(Bool())
    print(
        "SKIPPING EXT OUT BITS",
        attributes,
        "until we decide how to figure out https://github.com/PandABlocks/PandABlocks-ioc/blob/c1e8056abf3f680fa3840493eb4ac6ca2be31313/src/"
        "pandablocks_ioc/ioc.py#L1148-L1170",
    )
    return {}
    return attributes


#
#
def make_bit_mux_attributes(
    panda_name: PandaName,
    bit_mux_field_info: BitMuxFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        String(),
        description=bit_mux_field_info.description,
        handler=DefaultFieldHandler(panda_name),
        group=WidgetGroup.INPUTS.value,
        initial_value=initial_values[panda_name],
    )

    attributes[PandaName(field="DELAY")] = AttrRW(
        Int(),
        description="Clock delay on input.",
        handler=DefaultFieldHandler(panda_name),
        group=WidgetGroup.INPUTS.value,
    )

    # TODO: Add DRVL DRVH to `delay`.
    return attributes


def make_pos_mux_attributes(
    panda_name: PandaName,
    pos_mux_field_info: PosMuxFieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    enum_type = enum.Enum("Labels", pos_mux_field_info.labels)
    attributes[panda_name] = AttrRW(
        Enum(enum_type),
        description=pos_mux_field_info.description,
        group=WidgetGroup.INPUTS.value,
        initial_value=enum_type[initial_values[panda_name]],
    )
    return attributes


def make_uint_param_attributes(
    panda_name: PandaName,
    uint_param_field_info: UintFieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        Float(prec=0),
        description=uint_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=float(initial_values[panda_name]),
    )
    return attributes

    # TODO: set DRVL, DRVH, HOPR (new fastcs feature)


def make_uint_read_attributes(
    panda_name: PandaName,
    uint_read_field_info: UintFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Float(prec=0),
        description=uint_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=float(initial_values[panda_name]),
    )
    return attributes


def make_uint_write_attributes(
    panda_name: PandaName,
    uint_write_field_info: UintFieldInfo,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrW(
        Float(prec=0),
        description=uint_write_field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def make_int_param_attributes(
    panda_name: PandaName,
    int_param_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        Int(),
        description=int_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=int(initial_values[panda_name]),
    )
    return attributes


def make_int_read_attributes(
    panda_name: PandaName,
    int_read_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Int(),
        description=int_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=int(initial_values[panda_name]),
    )
    return attributes


def make_int_write_attributes(
    panda_name: PandaName,
    int_write_field_info: FieldInfo,
) -> dict[PandaName, Attribute]:
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrW(
        Int(),
        description=int_write_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
    )
    return attributes


def make_scalar_param_attributes(
    panda_name: PandaName,
    scalar_param_field_info: ScalarFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        Float(units=scalar_param_field_info.units),
        description=scalar_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=float(initial_values[panda_name]),
    )
    return attributes


def make_scalar_read_attributes(
    panda_name: PandaName,
    scalar_read_field_info: ScalarFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Float(),
        description=scalar_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=float(initial_values[panda_name]),
    )
    return attributes


def make_scalar_write_attributes(
    panda_name: PandaName,
    scalar_write_field_info: ScalarFieldInfo,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Float(),
        description=scalar_write_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
    )
    return attributes


def make_bit_param_attributes(
    panda_name: PandaName,
    bit_param_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        Bool(),
        description=bit_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        # Initial value is string "0"/"1".
        # TODO: Equip each read/readwrite field with a converter
        initial_value=bool(int(initial_values[panda_name])),
    )
    return attributes


def make_bit_read_attributes(
    panda_name: PandaName,
    bit_read_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        Bool(),
        description=bit_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=bool(int(initial_values[panda_name])),
    )
    return attributes


def make_bit_write_attributes(
    panda_name: PandaName,
    bit_write_field_info: FieldInfo,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrW(
        Bool(),
        description=bit_write_field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def make_action_write_attributes(
    panda_name: PandaName,
    action_write_field_info: FieldInfo,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrW(
        Bool(),
        description=action_write_field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def make_lut_param_attributes(
    panda_name: PandaName,
    lut_param_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrRW(
        String(),
        description=lut_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=initial_values[panda_name],
    )
    return attributes


def make_lut_read_attributes(
    panda_name: PandaName,
    lut_read_field_info: FieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        String(),
        description=lut_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=initial_values[panda_name],
    )
    return attributes


def make_lut_write_attributes(
    panda_name: PandaName,
    lut_read_field_info: FieldInfo,
):
    attributes: dict[PandaName, Attribute] = {}
    attributes[panda_name] = AttrR(
        String(),
        description=lut_read_field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def make_enum_param_attributes(
    panda_name: PandaName,
    enum_param_field_info: EnumFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}
    enum_type = enum.Enum("Labels", enum_param_field_info.labels)
    attributes[panda_name] = AttrRW(
        Enum(enum_type),
        description=enum_param_field_info.description,
        group=WidgetGroup.PARAMETERS.value,
        initial_value=enum_type[initial_values[panda_name]],
    )
    return attributes


def make_enum_read_attributes(
    panda_name: PandaName,
    enum_read_field_info: EnumFieldInfo,
    initial_values: RawInitialValuesType,
):
    attributes: dict[PandaName, Attribute] = {}

    enum_type = enum.Enum("Labels", enum_read_field_info.labels)

    attributes[panda_name] = AttrR(
        Enum(enum_type),
        description=enum_read_field_info.description,
        group=WidgetGroup.READBACKS.value,
        initial_value=enum_type[initial_values[panda_name]],
    )
    return attributes


def make_enum_write_attributes(
    panda_name: PandaName,
    enum_write_field_info: EnumFieldInfo,
):
    attributes: dict[PandaName, Attribute] = {}
    enum_type = enum.Enum("Labels", enum_write_field_info.labels)
    attributes[panda_name] = AttrW(
        Enum(enum_type),
        description=enum_write_field_info.description,
        group=WidgetGroup.OUTPUTS.value,
    )
    return attributes


def get_field_controller_from_field_info(
    panda_name: PandaName,
    field_info: ResponseType,
    initial_values: RawInitialValuesType,
) -> dict[PandaName, Attribute]:
    match field_info:
        case TableFieldInfo():
            return make_table_field_attributes(panda_name, field_info)
        # Time types
        case TimeFieldInfo(subtype=None):
            return make_time_param_attributes(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(type="param"):
            return make_time_param_attributes(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(subtype="read"):
            return make_time_read_attributes(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(subtype="write"):
            return make_time_write_attributes(panda_name, field_info)

        # Bit types
        case BitOutFieldInfo():
            return make_bit_out_attributes(panda_name, field_info, initial_values)
        case ExtOutBitsFieldInfo(subtype="timestamp"):
            return make_ext_out_attributes(panda_name, field_info)
        case ExtOutBitsFieldInfo():
            return make_ext_out_bits_attributes(panda_name, field_info)
        case ExtOutFieldInfo():
            return make_ext_out_attributes(panda_name, field_info)
        case BitMuxFieldInfo():
            return make_bit_mux_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="param", subtype="bit"):
            return make_bit_param_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="bit"):
            return make_bit_read_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="bit"):
            return make_bit_write_attributes(panda_name, field_info)

        # Pos types
        case PosOutFieldInfo():
            return make_pos_out_attributes(panda_name, field_info, initial_values)
        case PosMuxFieldInfo():
            return make_pos_mux_attributes(panda_name, field_info, initial_values)

        # Uint types
        case UintFieldInfo(type="param"):
            return make_uint_param_attributes(panda_name, field_info, initial_values)
        case UintFieldInfo(type="read"):
            return make_uint_read_attributes(panda_name, field_info, initial_values)
        case UintFieldInfo(type="write"):
            return make_uint_write_attributes(panda_name, field_info)

        # Scalar types
        case ScalarFieldInfo(subtype="param"):
            return make_scalar_param_attributes(panda_name, field_info, initial_values)
        case ScalarFieldInfo(type="read"):
            return make_scalar_read_attributes(panda_name, field_info, initial_values)
        case ScalarFieldInfo(type="write"):
            return make_scalar_write_attributes(panda_name, field_info)

        # Int types
        case FieldInfo(type="param", subtype="int"):
            return make_int_param_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="int"):
            return make_int_read_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="int"):
            return make_int_write_attributes(panda_name, field_info)

        # Action types
        case FieldInfo(
            type="write",
            subtype="action",
        ):
            return make_action_write_attributes(panda_name, field_info)

        # Lut types
        case FieldInfo(type="param", subtype="lut"):
            return make_lut_param_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="lut"):
            return make_lut_read_attributes(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="lut"):
            return make_lut_write_attributes(panda_name, field_info)

        # Enum types
        case EnumFieldInfo(type="param"):
            return make_enum_param_attributes(panda_name, field_info, initial_values)
        case EnumFieldInfo(type="read"):
            return make_enum_read_attributes(panda_name, field_info, initial_values)
        case EnumFieldInfo(type="write"):
            return make_enum_write_attributes(panda_name, field_info)
        case _:
            raise ValueError(f"Unknown field type: {type(field_info).__name__}.")
