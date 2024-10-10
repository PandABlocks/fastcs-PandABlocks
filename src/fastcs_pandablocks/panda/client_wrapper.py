"""
Over the years we've had to add little adjustments on top of the `BlockInfo`, `BlockAndFieldInfo`, etc.

This method has a `RawPanda` which handles all the io with the client.
"""

import asyncio
from dataclasses import dataclass
from pprint import pprint
from typing import TypedDict
from pandablocks.asyncio import AsyncioClient
from pandablocks.commands import (
    ChangeGroup,
    Changes,
    GetBlockInfo,
    GetChanges,
    GetFieldInfo,
)
from pandablocks.responses import (
    BlockInfo,
    Changes,
)

from fastcs_pandablocks.types import PandaName, ResponseType

class RawPanda:
    blocks: dict[str, BlockInfo] | None = None
    fields: list[dict[str, ResponseType]] | None = None
    metadata: dict[str, str] | None = None
    changes: dict[str, str] | None = None

    def __init__(self, host: str):
        self._client = AsyncioClient(host)
    
    async def connect(self):
        await self._client.connect()
        await self.introspect()

    async def disconnect(self):
        await self._client.close()
        self.blocks = None
        self.fields = None
        self.metadata = None
        self.changes = None
    
    async def introspect(self):
        self.blocks, self.fields, self.metadata, self.changes = {}, [], {}, {}
        self.blocks = await self._client.send(GetBlockInfo())
        self.fields = await asyncio.gather(
            *[self._client.send(GetFieldInfo(block)) for block in self.blocks],
        )
        initial_values = (await self._client.send(GetChanges(ChangeGroup.ALL, True))).values

        for field_name, value in initial_values.items():
            if field_name.startswith("*METADATA"):
                self.metadata[field_name] = value
            else:
                self.changes[field_name] = value

    async def get_changes(self):
        if not self.changes:
            raise RuntimeError("Panda not introspected.")
        self.changes = (await self._client.send(GetChanges(ChangeGroup.ALL, False))).values
        
    async def _ensure_connected(self):
        if not self.blocks:
            await self.connect()

    async def __aenter__(self):
        await self._ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.get_changes()
