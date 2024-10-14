import asyncio

from fastcs.controller import Controller
from fastcs.wrappers import scan

from fastcs_pandablocks.types.string_types import PandaName

from .blocks import Blocks
from .client_wrapper import RawPanda
from .types import EpicsName

POLL_PERIOD = 0.1


class PandaController(Controller):
    def __init__(self, prefix: EpicsName, hostname: str) -> None:
        self._raw_panda = RawPanda(hostname)
        self._blocks = Blocks(prefix)
        super().__init__()

    async def initialise(self) -> None: ...

    async def put_value_to_panda(self, name: PandaName, value: str):
        await self._raw_panda.send(str(name), value)

    async def connect(self) -> None:
        if (
            self._raw_panda.blocks is None
            or self._raw_panda.fields is None
            or self._raw_panda.metadata is None
            or self._raw_panda.changes is None
        ):
            await self._raw_panda.connect()

            assert self._raw_panda.blocks
            assert self._raw_panda.fields
            self._blocks.parse_introspected_data(
                self._raw_panda.blocks, self._raw_panda.fields
            )

    @scan(POLL_PERIOD)
    async def update(self):
        await self._raw_panda.get_changes()
        assert self._raw_panda.changes
        await asyncio.gather(
            *[
                self._blocks.update_field(PandaName(raw_panda_name), value)
                for raw_panda_name, value in self._raw_panda.changes.items()
            ]
        )
