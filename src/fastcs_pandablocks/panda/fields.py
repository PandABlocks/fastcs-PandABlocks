from __future__ import annotations

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

from fastcs_pandablocks.handlers import (
    CaptureHandler,
    DatasetHandler,
    DefaultFieldHandler,
    DefaultFieldSender,
    DefaultFieldUpdater,
    EguSender,
)
from fastcs_pandablocks.types import (
    PandaName,
    RawInitialValuesType,
    ResponseType,
    WidgetGroup,
)

# EPICS hardcoded. TODO: remove once we switch to pvxs.
MAXIMUM_DESCRIPTION_LENGTH = 40


def _strip_description(description: str | None) -> str | None:
    if description is None:
        return description
    return description[:MAXIMUM_DESCRIPTION_LENGTH]


class FieldController(SubController):
    def __init__(
        self,
        panda_name: PandaName,
        label: str | None = None,
    ):
        self.panda_name = panda_name
        self.top_level_attribute: Attribute | None = None

        # Sub fields eg `PGEN.OUT` and `PGEN.TRIGGER`
        self.sub_fields: dict[PandaName, FieldController] = {}

        self._additional_attributes: dict[str, Attribute] = {}

        super().__init__(search_device_for_attributes=False)

    def make_sub_fields(
        self,
        field_infos: dict[PandaName, ResponseType],
        initial_values: RawInitialValuesType,
    ):
        for sub_field_name, field_info in field_infos.items():
            full_sub_field_name = self.panda_name + sub_field_name
            field_initial_values = {
                key: value
                for key, value in initial_values.items()
                if key in sub_field_name
            }
            self.sub_fields[full_sub_field_name] = get_field_controller_from_field_info(
                full_sub_field_name, field_info, field_initial_values
            )

    async def initialise(self):
        for field_name, field in self.sub_fields.items():
            self.register_sub_controller(
                field_name.attribute_name, sub_controller=field
            )
            await field.initialise()
            if field.top_level_attribute:
                self._additional_attributes[field_name.attribute_name] = (
                    field.top_level_attribute
                )

    @property
    def additional_attributes(self) -> dict[str, Attribute]:
        """
        Used by the FastCS mapping parser to get attributes since
        we're not searching for device attributes.
        """
        return self._additional_attributes


class TableFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: TableFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name, field_info.description)

        self.top_level_attribute = AttrR(
            Float(),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )


class TimeParamFieldController(FieldController):
    # TODO: these `FieldInfo` are the exact same in pandablocks-client.
    def __init__(
        self,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo | TimeFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            Float(),
            handler=DefaultFieldHandler(panda_name),
            description=_strip_description(field_info.description),
            group=WidgetGroup.PARAMETERS.value,
        )
        self._additional_attributes["units"] = AttrW(
            String(),
            handler=EguSender(self.top_level_attribute),
            group=WidgetGroup.PARAMETERS.value,
            allowed_values=field_info.units_labels,
        )


class TimeReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Float(),
            handler=DefaultFieldUpdater(
                panda_name=panda_name,
            ),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )
        self._additional_attributes["units"] = AttrW(
            String(),
            handler=EguSender(self.top_level_attribute),
            group=WidgetGroup.OUTPUTS.value,
            allowed_values=field_info.units_labels,
        )


class TimeWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            Float(),
            handler=DefaultFieldSender(panda_name),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )
        self._additional_attributes["units"] = AttrW(
            String(),
            handler=EguSender(self.top_level_attribute),
            group=WidgetGroup.READBACKS.value,
            allowed_values=field_info.units_labels,
        )


class BitOutFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: BitOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )


class PosOutFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: PosOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        top_level_attribute = AttrR(
            Float(),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )

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
            await scaled.set(scale.get() * top_level_attribute.get() + offset.get())

        offset.set_update_callback(updated_scaled_on_offset_change)

        self._additional_attributes.update(
            {"scaled": scaled, "scale": scale, "offset": offset}
        )

        self.top_level_attribute = top_level_attribute
        self._additional_attributes["capture"] = AttrRW(
            String(),
            group=WidgetGroup.CAPTURE.value,
            handler=CaptureHandler(),
            allowed_values=field_info.capture_labels,
        )
        self._additional_attributes["dataset"] = AttrRW(
            String(),
            group=WidgetGroup.CAPTURE.value,
            handler=DatasetHandler(),
            allowed_values=field_info.capture_labels,
        )


class ExtOutFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: ExtOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)

        self.top_level_attribute = AttrR(
            Float(),
            description=_strip_description(field_info.description),
            group=WidgetGroup.OUTPUTS.value,
        )
        self._additional_attributes["capture"] = AttrRW(
            String(),
            group=WidgetGroup.CAPTURE.value,
            handler=CaptureHandler(),
            allowed_values=field_info.capture_labels,
        )
        self._additional_attributes["dataset"] = AttrRW(
            String(),
            group=WidgetGroup.CAPTURE.value,
            handler=DatasetHandler(),
            allowed_values=field_info.capture_labels,
        )


class _BitsSubFieldController(FieldController):
    def __init__(self, panda_name: PandaName, label: str):
        super().__init__(panda_name, label=label)

        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            description=_strip_description("Value of the field connected to this bit."),
            group=WidgetGroup.OUTPUTS.value,
        )
        self._additional_attributes["NAME"] = AttrR(
            String(),
            description="Name of the field connected to this bit.",
            initial_value=label,
        )


class ExtOutBitsFieldController(ExtOutFieldController):
    def __init__(
        self,
        panda_name: PandaName,
        field_info: ExtOutBitsFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name, field_info, initial_values)

        for bit_number, label in enumerate(field_info.bits, start=1):
            if label == "":
                continue  # Some rows are empty, do not create records.

            sub_field_panda_name = panda_name + PandaName(sub_field=f"bit{bit_number}")
            self.sub_fields[sub_field_panda_name] = _BitsSubFieldController(
                sub_field_panda_name, label=label
            )


class BitMuxFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        bit_mux_field_info: BitMuxFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            String(),
            description=_strip_description(bit_mux_field_info.description),
            handler=DefaultFieldHandler(panda_name),
            group=WidgetGroup.INPUTS.value,
        )

        self._additional_attributes["delay"] = AttrRW(
            Float(),
            description="Clock delay on input.",
            handler=DefaultFieldHandler(panda_name),
            group=WidgetGroup.INPUTS.value,
        )

        # TODO: Add DRVL DRVH to `delay`.


class PosMuxFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        pos_mux_field_info: PosMuxFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.INPUTS.value,
        )


class UintParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        uint_param_field_info: UintFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Float(prec=0),
            group=WidgetGroup.PARAMETERS.value,
        )


class UintReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        uint_read_field_info: UintFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Float(prec=0),
            group=WidgetGroup.READBACKS.value,
            # To be added once we have a pvxs backend
            # description=uint_read_field_info.description,
        )


class UintWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        uint_write_field_info: UintFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            Float(prec=0),
            group=WidgetGroup.OUTPUTS.value,
        )


class IntParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        int_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            Float(prec=0),
            group=WidgetGroup.PARAMETERS.value,
        )


class IntReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        int_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Int(),
            group=WidgetGroup.READBACKS.value,
        )


class IntWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        int_write_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            Int(),
            group=WidgetGroup.PARAMETERS.value,
        )


class ScalarParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        scalar_param_field_info: ScalarFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            Float(),
            group=WidgetGroup.PARAMETERS.value,
        )


class ScalarReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        scalar_read_field_info: ScalarFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.READBACKS.value,
        )


class ScalarWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        scalar_write_field_info: ScalarFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Float(),
            group=WidgetGroup.PARAMETERS.value,
        )


class BitParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        bit_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.PARAMETERS.value,
        )


class BitReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        bit_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.READBACKS.value,
        )


class BitWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        bit_write_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.OUTPUTS.value,
        )


class ActionReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        action_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.READBACKS.value,
        )


class ActionWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        action_write_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            Bool(znam="0", onam="1"),
            group=WidgetGroup.OUTPUTS.value,
        )


class LutParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        lut_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.PARAMETERS.value,
        )


class LutReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        lut_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.READBACKS.value,
        )


class LutWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        lut_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.OUTPUTS.value,
        )


class EnumParamFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        enum_param_field_info: EnumFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.allowed_values = enum_param_field_info.labels
        self.top_level_attribute = AttrRW(
            String(),
            group=WidgetGroup.PARAMETERS.value,
        )


class EnumReadFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        enum_read_field_info: EnumFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrR(
            String(),
            group=WidgetGroup.READBACKS.value,
        )


class EnumWriteFieldController(FieldController):
    def __init__(
        self,
        panda_name: PandaName,
        enum_write_field_info: EnumFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        super().__init__(panda_name)
        self.top_level_attribute = AttrW(
            String(),
            group=WidgetGroup.OUTPUTS.value,
        )


FieldControllerType = (
    TableFieldController
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
    | TimeParamFieldController
    | TimeReadFieldController
    | TimeWriteFieldController
)


def get_field_controller_from_field_info(
    panda_name: PandaName,
    field_info: ResponseType,
    initial_values: RawInitialValuesType,
) -> FieldControllerType:
    match field_info:
        case TableFieldInfo():
            return TableFieldController(panda_name, field_info, initial_values)
        # Time types
        case TimeFieldInfo(subtype=None):
            return TimeParamFieldController(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(type="param"):
            return TimeParamFieldController(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(subtype="read"):
            return TimeReadFieldController(panda_name, field_info, initial_values)
        case SubtypeTimeFieldInfo(subtype="write"):
            return TimeWriteFieldController(panda_name, field_info, initial_values)

        # Bit types
        case BitOutFieldInfo():
            return BitOutFieldController(panda_name, field_info, initial_values)
        case ExtOutBitsFieldInfo(subtype="timestamp"):
            return ExtOutFieldController(panda_name, field_info, initial_values)
        case ExtOutBitsFieldInfo():
            return ExtOutBitsFieldController(panda_name, field_info, initial_values)
        case ExtOutFieldInfo():
            return ExtOutFieldController(panda_name, field_info, initial_values)
        case BitMuxFieldInfo():
            return BitMuxFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="param", subtype="bit"):
            return BitParamFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="bit"):
            return BitReadFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="bit"):
            return BitWriteFieldController(panda_name, field_info, initial_values)

        # Pos types
        case PosOutFieldInfo():
            return PosOutFieldController(panda_name, field_info, initial_values)
        case PosMuxFieldInfo():
            return PosMuxFieldController(panda_name, field_info, initial_values)

        # Uint types
        case UintFieldInfo(type="param"):
            return UintParamFieldController(panda_name, field_info, initial_values)
        case UintFieldInfo(type="read"):
            return UintReadFieldController(panda_name, field_info, initial_values)
        case UintFieldInfo(type="write"):
            return UintWriteFieldController(panda_name, field_info, initial_values)

        # Scalar types
        case ScalarFieldInfo(subtype="param"):
            return ScalarParamFieldController(panda_name, field_info, initial_values)
        case ScalarFieldInfo(type="read"):
            return ScalarReadFieldController(panda_name, field_info, initial_values)
        case ScalarFieldInfo(type="write"):
            return ScalarWriteFieldController(panda_name, field_info, initial_values)

        # Int types
        case FieldInfo(type="param", subtype="int"):
            return IntParamFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="int"):
            return IntReadFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="int"):
            return IntWriteFieldController(panda_name, field_info, initial_values)

        # Action types
        case FieldInfo(
            type="read",
            subtype="action",
        ):
            return ActionReadFieldController(panda_name, field_info, initial_values)
        case FieldInfo(
            type="write",
            subtype="action",
        ):
            return ActionWriteFieldController(panda_name, field_info, initial_values)

        # Lut types
        case FieldInfo(type="param", subtype="lut"):
            return LutParamFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="read", subtype="lut"):
            return LutReadFieldController(panda_name, field_info, initial_values)
        case FieldInfo(type="write", subtype="lut"):
            return LutWriteFieldController(panda_name, field_info, initial_values)

        # Enum types
        case EnumFieldInfo(type="param"):
            return EnumParamFieldController(panda_name, field_info, initial_values)
        case EnumFieldInfo(type="read"):
            return EnumReadFieldController(panda_name, field_info, initial_values)
        case EnumFieldInfo(type="write"):
            return EnumWriteFieldController(panda_name, field_info, initial_values)
        case _:
            raise ValueError(f"Unknown field type: {type(field_info).__name__}.")
