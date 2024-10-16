import asyncio

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.datatypes import DataType, T
from fastcs.wrappers import scan

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.types import (
    PandaName,
)

from .client_wrapper import RawPanda
from .handlers import attribute_value_to_panda_value, panda_value_to_attribute_value


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        self.poll_period = poll_period

        self.attributes: dict[str, Attribute] = {}
        self._raw_panda = RawPanda(hostname)
        self._blocks: Blocks = Blocks(self._put_value_to_panda)

        self.connected = False

        super().__init__()

    async def _put_value_to_panda(
        self, panda_name: PandaName, fastcs_datatype: DataType[T], value: T
    ) -> None:
        await self._raw_panda.send(
            str(panda_name),
            attribute_value_to_panda_value(fastcs_datatype, value),
        )

    async def connect(self) -> None:
        if self.connected:
            # `connect` needs to be called in `initialise`,
            # then FastCS will attempt to call it again.
            return
        await self._raw_panda.connect()
        blocks, fields, labels, initial_values = await self._raw_panda.introspect()
        self._blocks.parse_introspected_data(blocks, fields, labels, initial_values)
        await self._blocks.setup_post_introspection()
        self.connected = True

    async def initialise(self) -> None:
        await self.connect()
        for block_name, block in self._blocks.top_level_controllers.items():
            self.register_sub_controller(block_name.attribute_name, block)

    def get_attribute(self, panda_name: PandaName) -> Attribute:
        assert panda_name.block
        block_controller = self._blocks.top_level_controllers[panda_name.up_to_block()]
        if panda_name.field is None:
            raise RuntimeError

        return block_controller.panda_name_to_attribute[panda_name]

    async def update_field_value(self, panda_name: PandaName, value: str):
        attribute = self._blocks.get_attribute(panda_name)
        attribute_value = panda_value_to_attribute_value(attribute.datatype, value)

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
