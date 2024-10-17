import asyncio

from fastcs.controller import Controller
from fastcs.wrappers import scan

from fastcs_pandablocks.types import PandaName

from .blocks import Blocks
from .client_wrapper import RawPanda


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        self._raw_panda = RawPanda(hostname)
        self._blocks = Blocks()
        self.is_connected = False

        super().__init__()

    async def connect(self) -> None:
        if self.is_connected:
            return

        await self._raw_panda.connect()

        assert self._raw_panda.blocks
        assert self._raw_panda.fields
        self._blocks.parse_introspected_data(
            self._raw_panda.blocks, self._raw_panda.fields
        )
        self.is_connected = True

    async def initialise(self) -> None:
        await self.connect()

        for attr_name, controller in self._blocks.flattened_attribute_tree():
            self.register_sub_controller(attr_name, controller)
            controller.initialise()

    # TODO https://github.com/DiamondLightSource/FastCS/issues/62
    @scan(0.1)
    async def update(self):
        await self._raw_panda.get_changes()
        assert self._raw_panda.changes
        await asyncio.gather(
            *[
                self._blocks.update_field_value(
                    PandaName.from_string(raw_panda_name), value
                )
                for raw_panda_name, value in self._raw_panda.changes.items()
            ]
        )
