"""
Over the years we've had to add little adjustments on top of the `BlockInfo`, `BlockAndFieldInfo`, etc.

This method has a `RawPanda` which handles all the io with the client.
"""

import asyncio
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

from fastcs_pandablocks.types import ResponseType


class RawPanda:
    _blocks: dict[str, BlockInfo] | None = None
    _metadata: tuple[Changes] | None = None

    _responses: list[dict[str, ResponseType]] | None = None
    _changes: Changes | None = None

    def __init__(self, host: str):
        self._client = AsyncioClient(host)
    
    async def connect(self): await self._client.connect()

    async def disconnect(self): await self._client.close()

    async def introspect(self):
        self._blocks = await self._client.send(GetBlockInfo())
        self._responses = await asyncio.gather(
            *[self._client.send(GetFieldInfo(block)) for block in self._blocks],
        )
        self._metadata = await self._client.send(GetChanges(ChangeGroup.ALL, True)),
    
    async def get_changes(self):
        self._changes = await self._client.send(GetChanges(ChangeGroup.ALL, False))
        

    async def _sync_with_panda(self):
        if not self._client.is_connected():
            await self.connect()
        await self.introspect()
    
    async def _ensure_connected(self):
        if not self._blocks:
            await self._sync_with_panda()

    async def __aenter__(self):
        await self._sync_with_panda()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._ensure_connected()
        await self.disconnect()

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self._ensure_connected()
        return await self.get_changes()
