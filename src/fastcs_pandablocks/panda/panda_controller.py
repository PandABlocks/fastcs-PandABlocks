import asyncio

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.cs_methods import Scan

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.types import PandaName

from .handlers import panda_value_to_attribute_value


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        super().__init__()

        self.attributes: dict[str, Attribute] = {}
        self._raw_panda = RawPanda(hostname)
        self._blocks: Blocks = Blocks(self._raw_panda)
        self.update = Scan(self._update, poll_period)

        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            # `connect` needs to be called in `initialise`,
            # then FastCS will attempt to call it again.
            return
        await self._raw_panda.connect()
        await self._blocks.parse_introspected_data()
        await self._blocks.setup_post_introspection()
        self.connected = True

    async def initialise(self) -> None:
        await self.connect()
        for block_name, block in self._blocks.controllers():
            self.register_sub_controller(block_name, block)

    async def update_field_value(self, panda_name: PandaName, value: str):
        attribute = self._blocks.get_attribute(panda_name)
        attribute_value = panda_value_to_attribute_value(attribute.datatype, value)

        if isinstance(attribute, AttrW) and not isinstance(attribute, AttrRW):
            await attribute.process(attribute_value)
        elif isinstance(attribute, AttrR):
            await attribute.set(attribute_value)
        else:
            raise RuntimeError(f"Couldn't find panda field for {panda_name}.")

    async def _update(self):
        changes = await self._raw_panda.get_changes()

        await asyncio.gather(
            *[
                self.update_field_value(PandaName.from_string(raw_panda_name), value)
                for raw_panda_name, value in changes.items()
            ]
        )
