import asyncio
from pprint import pprint
from typing import Callable
from dataclasses import dataclass
from .client_wrapper import RawPanda
from .blocks import Block
from fastcs_pandablocks.types import EpicsName, PandaName
from pandablocks.responses import Changes
import logging



class Panda:
    _raw_panda: RawPanda
    _blocks: dict[EpicsName, Block]
    POLL_PERIOD = 0.1

    def __init__(self, host: str):
        self._raw_panda = RawPanda(host)
        self._blocks = {}

    async def connect(self):
        logging.info("Connecting to the panda.")
        await self._raw_panda.connect()
        logging.info("Parsing data.")
        self._parse_introspected_data()

    def _parse_introspected_data(self):
        self._blocks = {}
        if (
            self._raw_panda.blocks is None or
            self._raw_panda.fields is None or
            self._raw_panda.metadata is None or
            self._raw_panda.changes is None
        ):
            raise ValueError("Panda not introspected.")

        for (block_name, block_info), raw_fields in zip(
            self._raw_panda.blocks.items(), self._raw_panda.fields
        ):
            self._blocks[EpicsName(block=block_name)] = Block(
                EpicsName(block=block_name),
                block_info.number,
                block_info.description,
                raw_fields
            )
        self._parse_changes()


    def _parse_changes(self):
        assert self._raw_panda.changes is not None
        for field_raw_name, field_value in self._raw_panda.changes.items():
            epics_name = PandaName.from_string(field_raw_name).to_epics_name()
            block = self._blocks[EpicsName(block=epics_name.block)]
            assert epics_name.field
            block.update_value(epics_name.block_number, epics_name.field, field_value)

    async def poll_for_changes(self):
        logging.info("Polling for data.")
        # We make this a coroutine so it can happen alongside the
        # sleep instead of before it.
        async def parse_changes():
            self._parse_changes()

        async for _ in self._raw_panda:
            await asyncio.gather(
                parse_changes(), 
                asyncio.sleep(self.POLL_PERIOD)
            )

    async def disconnect(self): await self._raw_panda.disconnect()
