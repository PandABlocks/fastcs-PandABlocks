import asyncio

from fastcs.controller import Controller
from fastcs.wrappers import scan

from fastcs_pandablocks import DEFAULT_POLL_PERIOD
from fastcs_pandablocks.types import PandaName

from .blocks import Blocks
from .client_wrapper import RawPanda


class PandaController(Controller):
    def __init__(self, hostname: str, poll_period: float) -> None:
        super().__init__()
        self._raw_panda = RawPanda(hostname)
        self._blocks = Blocks()

        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        #self.fastcs_method = Scan(self.update(), poll_period)

    async def initialise(self) -> None: ...

    async def connect(self) -> None:
        await self._raw_panda.connect()

        assert self._raw_panda.blocks
        assert self._raw_panda.fields
        self._blocks.parse_introspected_data(
            self._raw_panda.blocks, self._raw_panda.fields
        )
        for attr_name, controller in self._blocks.flattened_attribute_tree():
            self.register_sub_controller(attr_name, controller)

    @scan(DEFAULT_POLL_PERIOD) # TODO https://github.com/DiamondLightSource/FastCS/issues/62
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
