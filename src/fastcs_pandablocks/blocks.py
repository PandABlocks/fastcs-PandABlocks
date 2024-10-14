from pandablocks.responses import BlockInfo

from fastcs_pandablocks.types.string_types import EpicsName, PandaName

from .block import Block
from .types import ResponseType


class Blocks:
    _blocks: dict[str, Block]
    epics_prefix: EpicsName

    def __init__(self, prefix: EpicsName):
        self.prefix = prefix
        self._blocks = {}

    def parse_introspected_data(
        self, blocks: dict[str, BlockInfo], fields: list[dict[str, ResponseType]]
    ):
        self._blocks = {}

        for (block_name, block_info), raw_fields in zip(
            blocks.items(), fields, strict=True
        ):
            self._blocks[block_name] = Block(
                self.prefix + EpicsName(block=block_name),
                block_info.number,
                block_info.description,
                raw_fields,
            )

    async def update_field(self, panda_name: PandaName, value: str):
        assert panda_name.block
        await self._blocks[panda_name.block].update_field(panda_name, value)
