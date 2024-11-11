import asyncio

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.wrappers import scan

from fastcs_pandablocks.types import (
    PandaName,
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
)

from .client_wrapper import RawPanda
from .fields import FieldController


def _parse_introspected_data(
    raw_blocks: RawBlocksType,
    raw_field_infos: RawFieldsType,
    raw_labels: RawInitialValuesType,
    raw_initial_values: RawInitialValuesType,
):
    block_controllers: dict[PandaName, FieldController] = {}
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
            block = FieldController(
                numbered_block_name,
                label=block_info.description or label,
            )
            block.make_sub_fields(field_info, block_initial_values)
            block_controllers[numbered_block_name] = block

    return block_controllers


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        self.poll_period = poll_period

        self._additional_attributes: dict[str, Attribute] = {}
        self._raw_panda = RawPanda(hostname)
        self._blocks: dict[PandaName, FieldController] = {}

        self.connected = False

        super().__init__()

    @property
    def additional_attributes(self):
        return self._additional_attributes

    async def connect(self) -> None:
        if self.connected:
            # `connect` needs to be called in `initialise`,
            # then FastCS will attempt to call it again.
            return
        await self._raw_panda.connect()
        blocks, fields, labels, initial_values = await self._raw_panda.introspect()
        self._blocks = _parse_introspected_data(blocks, fields, labels, initial_values)
        self.connected = True

    async def initialise(self) -> None:
        await self.connect()
        for block_name, block in self._blocks.items():
            if block.top_level_attribute is not None:
                self._additional_attributes[block_name.attribute_name] = (
                    block.top_level_attribute
                )
            if block.additional_attributes or block.sub_fields:
                self.register_sub_controller(block_name.attribute_name, block)
            await block.initialise()

    def get_attribute(self, panda_name: PandaName) -> Attribute:
        assert panda_name.block
        block_controller = self._blocks[panda_name.up_to_block()]
        if panda_name.field is None:
            assert block_controller.top_level_attribute is not None
            return block_controller.top_level_attribute

        field_controller = block_controller.sub_fields[panda_name.up_to_field()]
        if panda_name.sub_field is None:
            assert field_controller.top_level_attribute is not None
            return field_controller.top_level_attribute

        sub_field_controller = field_controller.sub_fields[panda_name]
        assert sub_field_controller.top_level_attribute is not None
        return sub_field_controller.top_level_attribute

    async def update_field_value(self, panda_name: PandaName, value: str):
        attribute = self.get_attribute(panda_name)

        if isinstance(attribute, AttrW):
            await attribute.process(value)
        elif isinstance(attribute, (AttrRW | AttrR)):
            await attribute.set(value)
        else:
            raise RuntimeError(f"Couldn't find panda field for {panda_name}.")

    @scan(0.1)
    async def update(self):
        raise RuntimeError("FINALLY CALLED!")
        changes = await self._raw_panda.get_changes()
        await asyncio.gather(
            *[
                self.update_field_value(PandaName.from_string(raw_panda_name), value)
                for raw_panda_name, value in changes.items()
            ]
        )
