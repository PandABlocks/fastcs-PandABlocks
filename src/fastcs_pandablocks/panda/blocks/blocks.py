import asyncio
import enum
from collections.abc import Generator

import numpy as np
from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import SubController
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

from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.panda.handlers import (
    ArmSender,
    BitGroupOnUpdate,
    CaptureHandler,
    DefaultFieldHandler,
    DefaultFieldSender,
    DefaultFieldUpdater,
    TableFieldHandler,
)
from fastcs_pandablocks.types import (
    PandaName,
    RawInitialValuesType,
    ResponseType,
    WidgetGroup,
)

from .block_controller import BlockController
from .data import DataController, DatasetAttributes
from .versions import VersionController


class Blocks:
    """A wrapper that handles creating controllers and attributes from introspected
    panda data.

    Unfortunately attributes and names need to be cached throughout the introspection
    process so having this all in one (huge) file is the nicest way to handle this.
    """

    def __init__(self, raw_panda: RawPanda):
        self._raw_panda = raw_panda
        #: The controllers which should be registered by `PandaController` and are
        #: acccessible by panda name.
        self._introspected_controllers: dict[PandaName, BlockController] = {}

        #: For controllers we add on the fastcs side which aren't accessible
        #: by panda name.
        self._additional_controllers: dict[str, SubController] = {}

        #: For keeping track of ext out bits so that updates in the group can be linked
        self._bits_group_names: list[tuple[PandaName, list[PandaName]]] = []

        #: For keeping track of dataset records so the :Data:Datasets table
        #: can be updated.
        self._dataset_attributes: dict[PandaName, DatasetAttributes] = {}

    def get_attribute(self, panda_name: PandaName) -> Attribute:
        return self._introspected_controllers[
            panda_name.up_to_block()
        ].panda_name_to_attribute[panda_name]

    def controllers(self) -> Generator[tuple[str, SubController], None, None]:
        for (
            panda_name,
            introspected_controller,
        ) in self._introspected_controllers.items():
            yield panda_name.attribute_name, introspected_controller

        yield from self._additional_controllers.items()

    # ==================================================================================
    # ====== FOR LINKING AND GENERATING POST INTROSPECTION =============================
    # ==================================================================================

    async def setup_post_introspection(self):
        await asyncio.gather(
            self._link_bits_groups(),
            self._add_version_block(),
            self._add_pcap_arm(),
            self._add_data_block(),
        )

    async def _link_bits_groups(self):
        for group_panda_name, bit_panda_names in self._bits_group_names:
            group_attribute = self.get_attribute(group_panda_name)

            bit_attributes: list[AttrRW] = [
                self.get_attribute(panda_name) for panda_name in bit_panda_names
            ]  # type: ignore

            assert isinstance(group_attribute, AttrRW)
            update_callback = BitGroupOnUpdate(group_attribute, bit_attributes)
            group_attribute.add_update_callback(update_callback)

            for bit_attribute in bit_attributes:
                bit_attribute.description = (
                    "Whether this field is set for capture in "
                    f"the `{group_panda_name.up_to_field()}` group."
                )
                bit_attribute.add_update_callback(update_callback)

            # To match all bits before the p4p transport starts.
            await update_callback(group_attribute.get())

    async def _add_version_block(self):
        idn_response = await self._raw_panda.get("*IDN")
        assert isinstance(idn_response, str)
        self._additional_controllers["Versions"] = VersionController(idn_response)

    async def _add_pcap_arm(self):
        pcap_name = PandaName("PCAP")
        pcap_block = self._introspected_controllers.get(pcap_name, None)
        if pcap_block is None:
            raise ValueError("Did not receive a PCAP block during introspection.")

        pcap_block.add_attribute(
            pcap_name + PandaName(field="Arm"),
            AttrRW(
                Enum(ArmSender.ArmCommand),
                description="Arm/Disarm the PandA.",
                handler=ArmSender(self._raw_panda.arm, self._raw_panda.disarm),
                group=WidgetGroup.CAPTURE.value,
            ),
        )

    async def _add_data_block(self):
        self._additional_controllers["Data"] = DataController(
            self._raw_panda.data, self._dataset_attributes
        )

    # ==================================================================================
    # ====== FOR PARSING INTROSPECTED DATA =============================================
    # ==================================================================================

    async def parse_introspected_data(self):
        (
            raw_blocks,
            raw_field_infos,
            raw_labels,
            raw_initial_values,
        ) = await self._raw_panda.introspect()

        for (block_name, block_info), field_info in zip(
            raw_blocks.items(), raw_field_infos, strict=True
        ):
            numbered_block_names = (
                [block_name]
                if block_info.number in (None, 1)
                else [
                    block_name + PandaName(block_number=number)
                    for number in range(1, block_info.number + 1)
                ]
            )
            for numbered_block_name in numbered_block_names:
                block_initial_values = {
                    key: value
                    for key, value in raw_initial_values.items()
                    if key in numbered_block_name
                }
                label = raw_labels.get(numbered_block_name, None)
                block = BlockController(
                    numbered_block_name,
                    self._raw_panda.put_value_to_panda,
                    label=block_info.description or label,
                )
                self.fill_block(block, field_info, block_initial_values)

                self._introspected_controllers[numbered_block_name] = block

    def fill_block(
        self,
        block: BlockController,
        field_infos: dict[PandaName, ResponseType],
        initial_values: RawInitialValuesType,
    ):
        for field_panda_name, field_info in field_infos.items():
            full_field_name = block.panda_name + field_panda_name
            field_initial_values = {
                key: value
                for key, value in initial_values.items()
                if key in field_panda_name
            }
            self.add_field_to_block(
                block, full_field_name, field_info, field_initial_values
            )

    def add_field_to_block(
        self,
        parent_block: BlockController,
        field_panda_name: PandaName,
        field_info: ResponseType,
        initial_values: RawInitialValuesType,
    ):
        match field_info:
            case TableFieldInfo():
                return self._make_table_field(
                    parent_block, field_panda_name, field_info
                )
            case TimeFieldInfo(subtype=None):
                self._make_time_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case SubtypeTimeFieldInfo(type="param"):
                self._make_time_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case SubtypeTimeFieldInfo(subtype="read"):
                self._make_time_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case SubtypeTimeFieldInfo(subtype="write"):
                self._make_time_write(parent_block, field_panda_name, field_info)

            case BitOutFieldInfo():
                self._make_bit_out(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case ExtOutBitsFieldInfo(subtype="timestamp"):
                self._make_ext_out(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case ExtOutBitsFieldInfo():
                self._make_ext_out_bits(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case ExtOutFieldInfo():
                self._make_ext_out(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case BitMuxFieldInfo():
                self._make_bit_mux(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="param", subtype="bit"):
                self._make_bit_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="read", subtype="bit"):
                self._make_bit_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="write", subtype="bit"):
                self._make_bit_write(parent_block, field_panda_name, field_info)

            case PosOutFieldInfo():
                self._make_pos_out(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case PosMuxFieldInfo():
                self._make_pos_mux(
                    parent_block, field_panda_name, field_info, initial_values
                )

            # TODO: Add scaled as an option to fastcs int so we can have a uint32
            case UintFieldInfo(type="param"):
                self._make_uint_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case UintFieldInfo(type="read"):
                self._make_uint_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case UintFieldInfo(type="write"):
                self._make_uint_write(parent_block, field_panda_name, field_info)

            # Scalar types
            case ScalarFieldInfo(subtype="param"):
                self._make_scalar_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case ScalarFieldInfo(type="read"):
                self._make_scalar_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case ScalarFieldInfo(type="write"):
                self._make_scalar_write(parent_block, field_panda_name, field_info)

            # Int types
            case FieldInfo(type="param", subtype="int"):
                self._make_int_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="read", subtype="int"):
                self._make_int_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="write", subtype="int"):
                self._make_int_write(parent_block, field_panda_name, field_info)

            # Action types
            case FieldInfo(
                type="write",
                subtype="action",
            ):
                self._make_action_write(parent_block, field_panda_name, field_info)

            # Lut types
            case FieldInfo(type="param", subtype="lut"):
                self._make_lut_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="read", subtype="lut"):
                self._make_lut_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case FieldInfo(type="write", subtype="lut"):
                self._make_lut_write(parent_block, field_panda_name, field_info)

            # Enum types
            case EnumFieldInfo(type="param"):
                self._make_enum_param(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case EnumFieldInfo(type="read"):
                self._make_enum_read(
                    parent_block, field_panda_name, field_info, initial_values
                )
            case EnumFieldInfo(type="write"):
                self._make_enum_write(parent_block, field_panda_name, field_info)
            case _:
                raise ValueError(f"Unknown field type: {type(field_info).__name__}.")

    def _table_datatypes_from_table_field_details(
        self,
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

    def _make_table_field(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: TableFieldInfo,
    ):
        structured_datatype = [
            (name, self._table_datatypes_from_table_field_details(details))
            for name, details in field_info.fields.items()
        ]
        # TODO: Add units handler to update the units field and value of this one PV
        # https://github.com/PandABlocks/PandABlocks-ioc/blob/c1e8056abf3f680fa3840493eb4ac6ca2be31313/src/pandablocks_ioc/ioc.py#L750-L769
        parent_block.attributes[panda_name.attribute_name] = AttrRW(
            Table(structured_datatype),
            handler=TableFieldHandler(panda_name),
        )

    def _make_time_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo | TimeFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        # TODO: add a handler for units to scale to get seconds
        # The units come through in the same *CHANGES so there shouldn't
        # be a race condition here.
        # PandaName(block='PULSE', block_number=2, field='WIDTH', sub_field=None): '0',
        # PandaName(..., sub_field='UNITS'): 's',

        attribute = AttrRW(
            Float(units="s"),
            handler=DefaultFieldHandler(panda_name, self._raw_panda.put_value_to_panda),
            description=field_info.description,
            group=WidgetGroup.PARAMETERS.value,
            initial_value=float(initial_values[panda_name]),
        )
        parent_block.add_attribute(panda_name, attribute)

    def _make_time_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        attribute = AttrR(
            Float(units="s"),
            description=field_info.description,
            handler=DefaultFieldUpdater(panda_name),
            group=WidgetGroup.OUTPUTS.value,
            initial_value=float(initial_values[panda_name]),
        )
        parent_block.add_attribute(panda_name, attribute)

    def _make_time_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: SubtypeTimeFieldInfo,
    ):
        attribute = AttrW(
            Float(units="s"),
            handler=DefaultFieldHandler(panda_name, self._raw_panda.put_value_to_panda),
            description=field_info.description,
            group=WidgetGroup.OUTPUTS.value,
        )
        parent_block.add_attribute(panda_name, attribute)

    def _make_bit_out(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: BitOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Bool(),
                description=field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.OUTPUTS.value,
                initial_value=bool(int(initial_values[panda_name])),
            ),
        )

        capture_name = panda_name + PandaName(sub_field="CAPTURE")
        parent_block.add_attribute(
            capture_name,
            AttrRW(
                Bool(),
                group=WidgetGroup.CAPTURE.value,
                initial_value=False,
            ),
        )

    def _make_pos_out(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: PosOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        pos_out = AttrR(
            Int(),
            description=field_info.description,
            handler=DefaultFieldUpdater(panda_name),
            group=WidgetGroup.OUTPUTS.value,
            initial_value=int(initial_values[panda_name]),
        )
        parent_block.add_attribute(panda_name, pos_out)

        scale_panda_name = panda_name + PandaName(sub_field="SCALE")
        scale = AttrRW(
            Float(),
            group=WidgetGroup.CAPTURE.value,
            handler=DefaultFieldHandler(panda_name, self._raw_panda.put_value_to_panda),
            initial_value=float(initial_values[scale_panda_name]),
        )
        parent_block.add_attribute(scale_panda_name, scale)

        offset_panda_name = panda_name + PandaName(sub_field="OFFSET")
        offset = AttrRW(
            Float(),
            group=WidgetGroup.CAPTURE.value,
            handler=DefaultFieldHandler(panda_name, self._raw_panda.put_value_to_panda),
            initial_value=float(initial_values[offset_panda_name]),
        )
        parent_block.add_attribute(offset_panda_name, offset)

        scaled_panda_name = panda_name + PandaName(sub_field="SCALED")
        scaled = AttrR(
            Float(),
            group=WidgetGroup.CAPTURE.value,
            description="Value with scaling applied.",
            handler=DefaultFieldUpdater(scaled_panda_name),
            initial_value=scale.get() * pos_out.get() + offset.get(),
        )
        parent_block.add_attribute(scaled_panda_name, scaled)

        async def updated_scaled_on_offset_change(*_):
            await scaled.set(scale.get() * pos_out.get() + offset.get())

        offset.add_update_callback(updated_scaled_on_offset_change)
        scale.add_update_callback(updated_scaled_on_offset_change)
        pos_out.add_update_callback(updated_scaled_on_offset_change)

        capture_enum = Enum(enum.Enum("Capture", field_info.capture_labels))

        capture_panda_name = panda_name + PandaName(sub_field="CAPTURE")
        capture_attribute = AttrRW(
            capture_enum,
            description=field_info.description,
            group=WidgetGroup.CAPTURE.value,
            handler=CaptureHandler(
                capture_panda_name, self._raw_panda.put_value_to_panda
            ),
            initial_value=capture_enum.members[
                capture_enum.names.index(initial_values[capture_panda_name])
            ],
        )
        parent_block.add_attribute(
            capture_panda_name,
            capture_attribute,
        )
        dataset_attribute = AttrRW(
            String(),
            description=(
                "Used to adjust the dataset name to one more scientifically relevant"
            ),
            group=WidgetGroup.CAPTURE.value,
            initial_value="",
        )
        parent_block.add_attribute(
            panda_name + PandaName(sub_field="DATASET"),
            dataset_attribute,
        )
        self._dataset_attributes[panda_name] = DatasetAttributes(
            dataset_attribute, capture_attribute
        )

    def _make_ext_out(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: ExtOutFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        """Returns the capture attribtute so we can add a callback in ext out bits.

        For an ext out bits, we set one capture in the group, wait for the panda
        response that the group is being captutured, and then update all the elements
        in the group.
        """

        capture_enum = Enum(enum.Enum("Capture", field_info.capture_labels))
        capture_panda_name = panda_name + PandaName(sub_field="CAPTURE")
        capture_attribute = AttrRW(
            capture_enum,
            description=field_info.description,
            group=WidgetGroup.CAPTURE.value,
            handler=CaptureHandler(
                capture_panda_name, self._raw_panda.put_value_to_panda
            ),
            initial_value=capture_enum.enum_cls[initial_values[capture_panda_name]],
        )

        parent_block.add_attribute(capture_panda_name, capture_attribute)

        dataset_attribute = AttrRW(
            String(),
            description=(
                "Used to adjust the dataset name to one more scientifically relevant"
            ),
            group=WidgetGroup.CAPTURE.value,
            initial_value="",
        )
        parent_block.add_attribute(
            panda_name + PandaName(sub_field="DATASET"),
            dataset_attribute,
        )
        self._dataset_attributes[panda_name] = DatasetAttributes(
            dataset_attribute, capture_attribute
        )

    def _make_ext_out_bits(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        field_info: ExtOutBitsFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        self._make_ext_out(parent_block, panda_name, field_info, initial_values)
        capture_group_members = [
            PandaName.from_string(label) + PandaName(sub_field="CAPTURE")
            for label in field_info.bits
            if label != ""
        ]

        self._bits_group_names.append(
            (
                panda_name + PandaName(sub_field="CAPTURE"),
                capture_group_members,
            )
        )

    def _make_bit_mux(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        bit_mux_field_info: BitMuxFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                String(),
                description=bit_mux_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.INPUTS.value,
                initial_value=initial_values[panda_name],
            ),
        )

        delay_panda_name = panda_name + PandaName(sub_field="DELAY")
        parent_block.add_attribute(
            delay_panda_name,
            AttrRW(
                Int(min=0, max=bit_mux_field_info.max_delay),
                description="Clock delay on input.",
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.INPUTS.value,
                initial_value=int(initial_values[delay_panda_name]),
            ),
        )

    def _make_pos_mux(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        pos_mux_field_info: PosMuxFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        enum_type = enum.Enum("Labels", pos_mux_field_info.labels)
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Enum(enum_type),
                description=pos_mux_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.INPUTS.value,
                initial_value=enum_type[initial_values[panda_name]],
            ),
        )

    def _make_uint_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        uint_param_field_info: UintFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Float(prec=0, min=0, max=uint_param_field_info.max_val),
                description=uint_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=float(initial_values[panda_name]),
            ),
        )

    def _make_uint_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        uint_read_field_info: UintFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Float(prec=0, min=0, max=uint_read_field_info.max_val),
                description=uint_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=float(initial_values[panda_name]),
            ),
        )

    def _make_uint_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        uint_write_field_info: UintFieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrW(
                Float(prec=0, min=0, max=uint_write_field_info.max_val),
                description=uint_write_field_info.description,
                handler=DefaultFieldSender(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.OUTPUTS.value,
            ),
        )

    def _make_int_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        int_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Int(),
                description=int_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=int(initial_values[panda_name]),
            ),
        )

    def _make_int_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        int_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Int(),
                description=int_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=int(initial_values[panda_name]),
            ),
        )

    def _make_int_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        int_write_field_info: FieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrW(
                Int(),
                description=int_write_field_info.description,
                handler=DefaultFieldSender(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
            ),
        )

    def _make_scalar_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        scalar_param_field_info: ScalarFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Float(units=scalar_param_field_info.units),
                description=scalar_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=float(initial_values[panda_name]),
            ),
        )

    def _make_scalar_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        scalar_read_field_info: ScalarFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Float(),
                description=scalar_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=float(initial_values[panda_name]),
            ),
        )

    def _make_scalar_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        scalar_write_field_info: ScalarFieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Float(),
                description=scalar_write_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.PARAMETERS.value,
            ),
        )

    def _make_bit_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        bit_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Bool(),
                description=bit_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=bool(int(initial_values[panda_name])),
            ),
        )

    def _make_bit_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        bit_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                Bool(),
                description=bit_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=bool(int(initial_values[panda_name])),
            ),
        )

    def _make_bit_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        bit_write_field_info: FieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrW(
                Bool(),
                description=bit_write_field_info.description,
                handler=DefaultFieldSender(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.OUTPUTS.value,
            ),
        )

    def _make_action_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        action_write_field_info: FieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrW(
                Bool(),
                description=action_write_field_info.description,
                handler=DefaultFieldSender(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.OUTPUTS.value,
            ),
        )

    def _make_lut_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        lut_param_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                String(),
                description=lut_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=initial_values[panda_name],
            ),
        )

    def _make_lut_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        lut_read_field_info: FieldInfo,
        initial_values: RawInitialValuesType,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                String(),
                description=lut_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=initial_values[panda_name],
            ),
        )

    def _make_lut_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        lut_read_field_info: FieldInfo,
    ):
        parent_block.add_attribute(
            panda_name,
            AttrR(
                String(),
                handler=DefaultFieldUpdater(panda_name),
                description=lut_read_field_info.description,
                group=WidgetGroup.OUTPUTS.value,
            ),
        )

    def _make_enum_param(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        enum_param_field_info: EnumFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        enum_type = enum.Enum("Labels", enum_param_field_info.labels)
        parent_block.add_attribute(
            panda_name,
            AttrRW(
                Enum(enum_type),
                description=enum_param_field_info.description,
                handler=DefaultFieldHandler(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.PARAMETERS.value,
                initial_value=enum_type[initial_values[panda_name]],
            ),
        )

    def _make_enum_read(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        enum_read_field_info: EnumFieldInfo,
        initial_values: RawInitialValuesType,
    ):
        enum_type = enum.Enum("Labels", enum_read_field_info.labels)

        parent_block.add_attribute(
            panda_name,
            AttrR(
                Enum(enum_type),
                description=enum_read_field_info.description,
                handler=DefaultFieldUpdater(panda_name),
                group=WidgetGroup.READBACKS.value,
                initial_value=enum_type[initial_values[panda_name]],
            ),
        )

    def _make_enum_write(
        self,
        parent_block: BlockController,
        panda_name: PandaName,
        enum_write_field_info: EnumFieldInfo,
    ):
        enum_type = enum.Enum("Labels", enum_write_field_info.labels)
        parent_block.add_attribute(
            panda_name,
            AttrW(
                Enum(enum_type),
                description=enum_write_field_info.description,
                handler=DefaultFieldSender(
                    panda_name, self._raw_panda.put_value_to_panda
                ),
                group=WidgetGroup.OUTPUTS.value,
            ),
        )
