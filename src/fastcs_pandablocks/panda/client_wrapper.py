"""
This method has a `RawPanda` which handles all the io with the client.
"""

import asyncio
from collections.abc import AsyncGenerator

from fastcs.datatypes import DataType, T
from pandablocks.asyncio import AsyncioClient
from pandablocks.commands import (
    Arm,
    ChangeGroup,
    Disarm,
    Get,
    GetBlockInfo,
    GetChanges,
    GetFieldInfo,
    Put,
)
from pandablocks.responses import Data

from fastcs_pandablocks.types import (
    PandaName,
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
)

from .handlers import attribute_value_to_panda_value


class RawPanda:
    """A wrapper for interacting with pandablocks-client."""

    def __init__(self, hostname: str):
        self._client = AsyncioClient(host=hostname)

    async def connect(self):
        await self._client.connect()

    async def disconnect(self):
        await self._client.close()

    async def put_value_to_panda(
        self, panda_name: PandaName, fastcs_datatype: DataType[T], value: T
    ) -> None:
        await self.send(
            str(panda_name),
            attribute_value_to_panda_value(fastcs_datatype, value),
        )

    async def introspect(
        self,
    ) -> tuple[
        RawBlocksType, RawFieldsType, RawInitialValuesType, RawInitialValuesType
    ]:
        blocks, fields, labels, initial_values = {}, [], {}, {}

        blocks = {
            PandaName.from_string(name): block_info
            for name, block_info in (await self._client.send(GetBlockInfo())).items()
        }
        fields = [
            {
                PandaName(field=name): field_info
                for name, field_info in block_values.items()
            }
            for block_values in await asyncio.gather(
                *[self._client.send(GetFieldInfo(str(block))) for block in blocks]
            )
        ]

        field_data = (await self._client.send(GetChanges(ChangeGroup.ALL, True))).values

        for field_name, value in field_data.items():
            if field_name.startswith("*METADATA"):
                field_name_without_prefix = field_name.removeprefix("*METADATA.")
                if field_name_without_prefix == "DESIGN":
                    continue  # TODO: Handle design.
                elif not field_name_without_prefix.startswith("LABEL_"):
                    raise TypeError(
                        "Received metadata not corresponding to a `LABEL_`: "
                        f"{field_name} = {value}."
                    )
                labels[
                    PandaName.from_string(
                        field_name_without_prefix.removeprefix("LABEL_")
                    )
                ] = value
            else:  # Field is a default value
                initial_values[PandaName.from_string(field_name)] = value

        return blocks, fields, labels, initial_values

    async def send(self, name: str, value: str):
        await self._client.send(Put(name, value))

    async def get(self, name: str) -> str | list[str]:
        return await self._client.send(Get(name))

    async def get_changes(self) -> dict[str, str]:
        return (await self._client.send(GetChanges(ChangeGroup.ALL, False))).values

    async def arm(self):
        await self._client.send(Arm())

    async def disarm(self):
        await self._client.send(Disarm())

    async def data(
        self, scaled: bool, flush_period: float
    ) -> AsyncGenerator[Data, None]:
        async for data in self._client.data(scaled=scaled, flush_period=flush_period):
            yield data
