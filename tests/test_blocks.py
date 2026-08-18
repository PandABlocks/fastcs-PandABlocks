from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastcs.attributes import AttrR, AttrRW
from fastcs.methods import Command
from pandablocks.commands import Put
from pandablocks.responses import TableFieldDetails, TableFieldInfo

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.blocks.block_controller import BlockController
from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.panda.io.arm import ArmIO
from fastcs_pandablocks.panda.io.default import DefaultFieldIO
from fastcs_pandablocks.panda.io.table import (
    Mode,
    NextWrite,
    TableFieldIO,
    TableFieldIORef,
)
from fastcs_pandablocks.panda.io.units import UnitsIO
from fastcs_pandablocks.types import PandaName, WidgetGroup


@pytest.fixture
def mock_raw_panda_block():
    """Fixture to set up a Block instance and a raw panda with mocked transport."""

    raw_panda = RawPanda("localhost")
    raw_panda._client = AsyncMock()
    parent = BlockController(PandaName("test"), raw_panda.put_value_to_panda)
    ios = [ArmIO(), DefaultFieldIO(), TableFieldIO(), UnitsIO()]
    return Blocks(raw_panda, ios), parent, raw_panda


@pytest.mark.asyncio
async def test_make_table_field_with_mode(mock_raw_panda_block):
    """Test that _make_table_field creates expected attrs for has_mode tables."""
    block, parent, raw_panda = mock_raw_panda_block
    table_field_details = TableFieldDetails("int", 0, 1)
    table_field_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="",
        max_length=10,
        fields={"FIELD": table_field_details},
        row_words=1,  # Must be > 0 for words_to_table to work
        has_mode=True,
    )

    block_name = PandaName("test_block")
    initial_values = {block_name: ["0"]}
    block._make_table_field(parent, block_name, table_field_info, initial_values)

    # Verify that NEXT_WRITE was created as a local-only AttrRW (must be
    # AttrRW, not a plain AttrW, so TableFieldIO.send can read it via .get()).
    next_write_name = block_name + PandaName(sub_field="NEXT_WRITE")
    assert next_write_name in parent.panda_name_to_attribute
    next_write_attr = parent.panda_name_to_attribute[next_write_name]
    assert isinstance(next_write_attr, AttrRW)
    # Verify it's a local-only attribute (no io_ref) by checking internal state
    assert not hasattr(next_write_attr, "_io_ref") or next_write_attr._io_ref is None

    # Verify that MODE was created with PARAMETERS group
    mode_name = block_name + PandaName(sub_field="MODE")
    assert mode_name in parent.panda_name_to_attribute
    mode_attr = parent.panda_name_to_attribute[mode_name]
    assert isinstance(mode_attr, AttrR)
    assert mode_attr.group == WidgetGroup.PARAMETERS.value
    assert mode_attr.datatype.dtype is Mode

    # Verify that QUEUED_LINES was created with PARAMETERS group
    queued_lines_name = block_name + PandaName(sub_field="QUEUED_LINES")
    assert queued_lines_name in parent.panda_name_to_attribute
    queued_lines_attr = parent.panda_name_to_attribute[queued_lines_name]
    assert isinstance(queued_lines_attr, AttrR)
    assert queued_lines_attr.group == WidgetGroup.PARAMETERS.value

    # Verify that CLEAR command was added to parent with qualified name
    clear_attr_name = (block_name + PandaName(sub_field="CLEAR")).attribute_name
    assert hasattr(parent, clear_attr_name)
    clear_cmd = getattr(parent, clear_attr_name)
    assert isinstance(clear_cmd, Command)
    await clear_cmd()
    raw_panda._client.send.assert_awaited_once()
    command = raw_panda._client.send.await_args.args[0]
    assert isinstance(command, Put)
    assert command.field == str(block_name)
    assert command.value == []

    # Verify table io_ref has append support and a NEXT_WRITE reference
    table_attr = parent.panda_name_to_attribute[block_name]
    assert isinstance(table_attr.io_ref, TableFieldIORef)
    assert table_attr.io_ref.next_write_attr is not None
    assert table_attr.io_ref.next_write_attr is next_write_attr
    # Verify append_to_panda is wired to the raw panda append callable.
    assert callable(table_attr.io_ref.append_to_panda)
    assert table_attr.io_ref.append_to_panda.__name__ == "append_to_panda"


@pytest.mark.asyncio
async def test_table_field_send_reads_real_next_write_attr(mock_raw_panda_block):
    """Regression test for a production crash: TableFieldIO.send() must be able
    to read the NEXT_WRITE attribute exactly as _make_table_field wires it up
    (a local AttrRW), not just a test stub with a `.get()` method. Previously
    NEXT_WRITE was a plain AttrW, which has no `.get()`, so every write to a
    has_mode table crashed with AttributeError: 'AttrW' object has no
    attribute 'get'.
    """
    block, parent, raw_panda = mock_raw_panda_block
    table_field_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="",
        max_length=10,
        fields={"FIELD": TableFieldDetails("int", 0, 1)},
        row_words=1,
        has_mode=True,
    )

    block_name = PandaName("test_block")
    initial_values = {block_name: ["0"]}
    block._make_table_field(parent, block_name, table_field_info, initial_values)

    next_write_name = block_name + PandaName(sub_field="NEXT_WRITE")
    next_write_attr = parent.panda_name_to_attribute[next_write_name]
    await next_write_attr.put(NextWrite.APPEND)

    table_attr = parent.panda_name_to_attribute[block_name]
    raw_panda._client.reset_mock()
    await TableFieldIO().send(table_attr, np.array([(1,)], dtype=[("field", np.int32)]))

    raw_panda._client.send.assert_awaited_once()
    command = raw_panda._client.send.await_args.args[0]
    assert command.field == str(block_name)
    assert command.last is False


@pytest.mark.asyncio
async def test_make_table_field_without_mode(mock_raw_panda_block):
    """Test that _make_table_field works correctly for tables without has_mode."""
    block, parent, raw_panda = mock_raw_panda_block
    table_field_details = TableFieldDetails("int", 0, 1)
    table_field_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="",
        max_length=10,
        fields={"FIELD": table_field_details},
        row_words=1,  # Must be > 0 for words_to_table to work
        has_mode=False,
    )

    block_name = PandaName("test_block_no_mode")
    initial_values = {block_name: ["0"]}
    block._make_table_field(parent, block_name, table_field_info, initial_values)

    # Verify that no NEXT_WRITE/MODE/QUEUED_LINES attributes were created
    next_write_name = block_name + PandaName(sub_field="NEXT_WRITE")
    assert next_write_name not in parent.panda_name_to_attribute

    mode_name = block_name + PandaName(sub_field="MODE")
    assert mode_name not in parent.panda_name_to_attribute

    queued_lines_name = block_name + PandaName(sub_field="QUEUED_LINES")
    assert queued_lines_name not in parent.panda_name_to_attribute

    # Verify that no clear command was added
    clear_attr_name = (block_name + PandaName(sub_field="CLEAR")).attribute_name
    assert not hasattr(parent, clear_attr_name)

    # Verify that the table attribute's io_ref has next_write_attr = None
    table_attr = parent.panda_name_to_attribute[block_name]
    assert isinstance(table_attr.io_ref, TableFieldIORef)
    assert table_attr.io_ref.next_write_attr is None


@pytest.mark.asyncio
async def test_make_table_field_multiple_has_mode_tables(mock_raw_panda_block):
    """Test that multiple has_mode tables on same block have independent CLEARs."""
    block, parent, raw_panda = mock_raw_panda_block
    table_field_details = TableFieldDetails("int", 0, 1)

    # Create two has_mode tables under the same block
    # Use field-level names to create unique attribute names
    table1_field = PandaName(field="TABLE1")
    table1_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="First table",
        max_length=10,
        fields={"FIELD": table_field_details},
        row_words=1,
        has_mode=True,
    )
    initial_values = {table1_field: ["0"]}
    block._make_table_field(parent, table1_field, table1_info, initial_values)

    table2_field = PandaName(field="TABLE2")
    table2_info = TableFieldInfo(
        type="int",
        subtype=None,
        description="Second table",
        max_length=10,
        fields={"FIELD": table_field_details},
        row_words=1,
        has_mode=True,
    )
    initial_values = {table2_field: ["0"]}
    block._make_table_field(parent, table2_field, table2_info, initial_values)

    # Verify both CLEAR commands exist with qualified names
    table1_clear_attr_name = (
        table1_field + PandaName(sub_field="CLEAR")
    ).attribute_name
    table2_clear_attr_name = (
        table2_field + PandaName(sub_field="CLEAR")
    ).attribute_name

    assert hasattr(parent, table1_clear_attr_name)
    assert hasattr(parent, table2_clear_attr_name)

    table1_clear = getattr(parent, table1_clear_attr_name)
    table2_clear = getattr(parent, table2_clear_attr_name)

    assert isinstance(table1_clear, Command)
    assert isinstance(table2_clear, Command)

    # Verify they are independent commands (calling table1's clear sends for table1)
    raw_panda._client.reset_mock()
    await table1_clear()
    raw_panda._client.send.assert_awaited_once()
    command = raw_panda._client.send.await_args.args[0]
    assert isinstance(command, Put)
    assert command.field == str(table1_field)
    assert command.value == []

    # Verify table2's clear is independent (calling table2's clear sends for table2)
    raw_panda._client.reset_mock()
    await table2_clear()
    raw_panda._client.send.assert_awaited_once()
    command = raw_panda._client.send.await_args.args[0]
    assert isinstance(command, Put)
    assert command.field == str(table2_field)
    assert command.value == []
