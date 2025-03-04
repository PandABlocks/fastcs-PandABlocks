import asyncio

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller, SubController
from fastcs.datatypes import Bool, Float, Int, String, T
from fastcs.wrappers import scan

from fastcs_pandablocks.types import (
    PandaName,
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
)
from fastcs_pandablocks.types._annotations import ResponseType

from .client_wrapper import RawPanda
from .fields import make_attributes


class BlockController(SubController):
    def __init__(self, panda_name: PandaName, label: str | None = None):
        self.description = label
        self.panda_name = panda_name

        self.attributes: dict[str, Attribute] = {}
        self.panda_name_to_attribute: dict[PandaName, Attribute] = {}
        super().__init__()

    def make_attributes(
        self,
        field_info: dict[PandaName, ResponseType],
        initial_values: dict[PandaName, str],
    ):
        if self.description is not None:
            self.attributes["LABEL"] = AttrR(
                String(),
                description="Label from metadata.",
                initial_value=self.description,
            )
        self.panda_name_to_attribute = make_attributes(
            self.panda_name, field_info, initial_values
        )
        attribute_name_to_attribute = {}
        for panda_name, attribute in self.panda_name_to_attribute.items():
            assert panda_name.field
            sub_field = f"_{panda_name.sub_field}" if panda_name.sub_field else ""
            attribute_name_to_attribute[f"{panda_name.field}{sub_field}"] = attribute

        self.attributes.update(attribute_name_to_attribute)


def _parse_introspected_data(
    raw_blocks: RawBlocksType,
    raw_field_infos: RawFieldsType,
    raw_labels: RawInitialValuesType,
    raw_initial_values: RawInitialValuesType,
):
    block_controllers: dict[PandaName, BlockController] = {}
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
                label=block_info.description or label,
            )
            block.make_attributes(field_info, block_initial_values)
            block_controllers[numbered_block_name] = block

    return block_controllers


def panda_value_to_attribute_value(attribute: Attribute[T], value: str) -> T:
    if isinstance(attribute.datatype, (Int | Float | String | Bool)):
        return attribute.datatype.dtype(value)  # type: ignore
    raise NotImplementedError(f"Unknown datatype {attribute.datatype}")


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        self.poll_period = poll_period

        self.attributes: dict[str, Attribute] = {}
        self._raw_panda = RawPanda(hostname)
        self._blocks: dict[PandaName, BlockController] = {}

        self.connected = False

        super().__init__()

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
            self.register_sub_controller(block_name.attribute_name.title(), block)

    def get_attribute(self, panda_name: PandaName) -> Attribute:
        assert panda_name.block
        block_controller = self._blocks[panda_name.up_to_block()]
        if panda_name.field is None:
            raise RuntimeError

        return block_controller.panda_name_to_attribute[panda_name]

    async def update_field_value(self, panda_name: PandaName, value: str):
        attribute = self.get_attribute(panda_name)
        attribute_value = panda_value_to_attribute_value(attribute, value)

        if isinstance(attribute, AttrW) and not isinstance(attribute, AttrRW):
            await attribute.process(attribute_value)
        elif isinstance(attribute, AttrR):
            await attribute.set(attribute_value)
        else:
            raise RuntimeError(f"Couldn't find panda field for {panda_name}.")

    @scan(0.1)
    async def update(self):
        changes = await self._raw_panda.get_changes()
        await asyncio.gather(
            *[
                self.update_field_value(PandaName.from_string(raw_panda_name), value)
                for raw_panda_name, value in changes.items()
            ]
        )
