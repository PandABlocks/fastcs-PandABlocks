from pprint import pprint
from typing import Callable
from dataclasses import dataclass
from .client_wrapper import RawPanda
from .blocks import Block
from fastcs_pandablocks.types import EpicsName, PandaName
from pandablocks.responses import Changes



class Panda:
    _raw_panda: RawPanda
    _blocks: dict[EpicsName, Block]

    def __init__(self, host: str):
        self._raw_panda = RawPanda(host)
        self._blocks = {}

    async def connect(self):
        await self._raw_panda._sync_with_panda()
        self._parse_introspected_data()

    def _parse_introspected_data(self):
        self._blocks = {}
        if (
            self._raw_panda._blocks is None or self._raw_panda._responses is None
        ):
            raise ValueError("Panda not introspected.")

        for (block_name, block_info), raw_fields in zip(
            self._raw_panda._blocks.items(), self._raw_panda._responses
        ):
            self._blocks[EpicsName(block=block_name)] = Block(
                EpicsName(block_name),
                block_info.number,
                block_info.description,
                raw_fields
            )

    
    def _parse_values(self, changes: Changes):
        for panda_name, field_value in changes.values.items():
            epics_name = PandaName(panda_name).to_epics_name()
            self._blocks[epics_name.block].change_value(
                field_value, epics_name.block_number, epics_name.field
            )



    
    async def disconnect(self): await self._raw_panda.disconnect()
