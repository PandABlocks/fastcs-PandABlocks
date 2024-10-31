"""
This method has a `RawPanda` which handles all the io with the client.
"""

import asyncio

from pandablocks.asyncio import AsyncioClient
from pandablocks.commands import (
    ChangeGroup,
    GetBlockInfo,
    GetChanges,
    GetFieldInfo,
    Put,
)

from fastcs_pandablocks.types import (
    PandaName,
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
)


class RawPanda:
    def __init__(self, hostname: str):
        self._client = AsyncioClient(host=hostname)

    async def connect(self):
        await self._client.connect()

    async def disconnect(self):
        await self._client.close()

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

    async def get_changes(self) -> dict[str, str]:
        return (await self._client.send(GetChanges(ChangeGroup.ALL, False))).values
