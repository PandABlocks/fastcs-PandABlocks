from unittest.mock import AsyncMock

import pytest
from fastcs.datatypes import Int
from pandablocks.commands import Append

from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.types import PandaName


@pytest.mark.asyncio
async def test_append_to_panda_sends_append_command():
    raw_panda = RawPanda("localhost")
    raw_panda._client = AsyncMock()

    await raw_panda.append_to_panda(
        PandaName.from_string("SEQ1.TABLE"),
        Int(),
        ["1", "2"],
        last=True,
    )

    raw_panda._client.send.assert_awaited_once()
    command = raw_panda._client.send.await_args.args[0]
    assert isinstance(command, Append)
    assert command.field == "SEQ1.TABLE"
    assert command.value == ["1", "2"]
    assert command.last is True
