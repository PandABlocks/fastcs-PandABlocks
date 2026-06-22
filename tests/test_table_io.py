from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastcs.datatypes import Table
from pandablocks.responses import TableFieldDetails, TableFieldInfo

from fastcs_pandablocks.panda.io.table import NextWrite, TableFieldIO, TableFieldIORef
from fastcs_pandablocks.types import PandaName


class _DummyNextWriteAttr:
    def __init__(self, value: NextWrite):
        self._value = value

    def get(self):
        return self._value


def _make_attr(next_write_value: NextWrite | None):
    put_value_to_panda = AsyncMock()
    append_to_panda = AsyncMock()

    field_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="",
        max_length=10,
        fields={"field": TableFieldDetails("int", 0, 1)},
        row_words=1,
        has_mode=next_write_value is not None,
    )

    next_write_attr = (
        _DummyNextWriteAttr(next_write_value) if next_write_value is not None else None
    )

    io_ref = TableFieldIORef(
        panda_name=PandaName("TEST.TABLE"),
        field_info=field_info,
        put_value_to_panda=put_value_to_panda,
        append_to_panda=append_to_panda,
        next_write_attr=next_write_attr,
    )

    # TableFieldIO.send only needs `datatype` and `io_ref` on the attribute object.
    attr = SimpleNamespace(datatype=Table([("field", np.int32)]), io_ref=io_ref)

    return attr, put_value_to_panda, append_to_panda


@pytest.mark.asyncio
async def test_table_field_io_send_uses_put_for_non_has_mode():
    attr, put_value_to_panda, append_to_panda = _make_attr(next_write_value=None)

    with (
        patch(
            "fastcs_pandablocks.panda.io.table.attribute_value_to_panda_value",
            return_value={"FIELD": [1]},
        ),
        patch("fastcs_pandablocks.panda.io.table.table_to_words", return_value=["1"]),
    ):
        await TableFieldIO().send(
            cast(Any, attr), np.zeros(1, dtype=[("field", np.int32)])
        )

    put_value_to_panda.assert_awaited_once_with(
        attr.io_ref.panda_name, attr.datatype, ["1"]
    )
    append_to_panda.assert_not_awaited()


@pytest.mark.asyncio
async def test_table_field_io_send_uses_put_for_replace():
    attr, put_value_to_panda, append_to_panda = _make_attr(
        next_write_value=NextWrite.REPLACE
    )

    with (
        patch(
            "fastcs_pandablocks.panda.io.table.attribute_value_to_panda_value",
            return_value={"FIELD": [2]},
        ),
        patch("fastcs_pandablocks.panda.io.table.table_to_words", return_value=["2"]),
    ):
        await TableFieldIO().send(
            cast(Any, attr), np.zeros(1, dtype=[("field", np.int32)])
        )

    put_value_to_panda.assert_awaited_once_with(
        attr.io_ref.panda_name, attr.datatype, ["2"]
    )
    append_to_panda.assert_not_awaited()


@pytest.mark.asyncio
async def test_table_field_io_send_uses_append_for_append():
    attr, put_value_to_panda, append_to_panda = _make_attr(
        next_write_value=NextWrite.APPEND
    )

    with (
        patch(
            "fastcs_pandablocks.panda.io.table.attribute_value_to_panda_value",
            return_value={"FIELD": [3]},
        ),
        patch("fastcs_pandablocks.panda.io.table.table_to_words", return_value=["3"]),
    ):
        await TableFieldIO().send(
            cast(Any, attr), np.zeros(1, dtype=[("field", np.int32)])
        )

    append_to_panda.assert_awaited_once_with(
        attr.io_ref.panda_name, attr.datatype, ["3"], False
    )
    put_value_to_panda.assert_not_awaited()


@pytest.mark.asyncio
async def test_table_field_io_send_uses_append_last_for_append_last():
    attr, put_value_to_panda, append_to_panda = _make_attr(
        next_write_value=NextWrite.APPEND_LAST
    )

    with (
        patch(
            "fastcs_pandablocks.panda.io.table.attribute_value_to_panda_value",
            return_value={"FIELD": [4]},
        ),
        patch("fastcs_pandablocks.panda.io.table.table_to_words", return_value=["4"]),
    ):
        await TableFieldIO().send(
            cast(Any, attr), np.zeros(1, dtype=[("field", np.int32)])
        )

    append_to_panda.assert_awaited_once_with(
        attr.io_ref.panda_name, attr.datatype, ["4"], True
    )
    put_value_to_panda.assert_not_awaited()
