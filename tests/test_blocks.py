from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastcs.attributes import AttrR, AttrW
from fastcs.methods import Command
from pandablocks.responses import TableFieldDetails, TableFieldInfo

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.blocks.block_controller import BlockController
from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.panda.io.arm import ArmIO
from fastcs_pandablocks.panda.io.default import DefaultFieldIO
from fastcs_pandablocks.panda.io.table import TableFieldIO, TableFieldIORef
from fastcs_pandablocks.panda.io.units import UnitsIO
from fastcs_pandablocks.types import PandaName, WidgetGroup


class MockRawPanda(RawPanda):
    def __init__(self):
        self._client = AsyncMock()
        self.put_value_to_panda = AsyncMock()
        self.append_to_panda = AsyncMock()
        self.send = AsyncMock()
        self.get = AsyncMock(return_value="mock_value")


@pytest.fixture
def mock_raw_panda_block():
    """Fixture to set up a Block instance and a mock raw_panda."""

    raw_panda = MockRawPanda()
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
        fields={"field": table_field_details},
        row_words=1,  # Must be > 0 for words_to_table to work
        has_mode=True,
    )

    block_name = PandaName("test_block")
    initial_values = {block_name: ["0"]}

    # Create mock table data for panda_value_to_attribute_value
    mock_table_data = np.array([(0,)], dtype=[("field", np.int32)])

    # Patch the low-level conversion to avoid integration complexity
    with patch(
        "fastcs_pandablocks.panda.blocks.blocks.panda_value_to_attribute_value",
        return_value=mock_table_data,
    ):
        # Call the method under test
        block._make_table_field(parent, block_name, table_field_info, initial_values)

    # Verify that NEXT_WRITE was created (should be AttrW without io_ref)
    next_write_name = block_name + PandaName(sub_field="NEXT_WRITE")
    assert next_write_name in parent.panda_name_to_attribute
    next_write_attr = parent.panda_name_to_attribute[next_write_name]
    assert isinstance(next_write_attr, AttrW)
    # Verify it's a local-only attribute (no io_ref) by checking internal state
    assert not hasattr(next_write_attr, "_io_ref") or next_write_attr._io_ref is None

    # Verify that MODE was created with PARAMETERS group
    mode_name = block_name + PandaName(sub_field="MODE")
    assert mode_name in parent.panda_name_to_attribute
    mode_attr = parent.panda_name_to_attribute[mode_name]
    assert isinstance(mode_attr, AttrR)
    assert mode_attr.group == WidgetGroup.PARAMETERS.value

    # Verify that QUEUED_LINES was created with PARAMETERS group
    queued_lines_name = block_name + PandaName(sub_field="QUEUED_LINES")
    assert queued_lines_name in parent.panda_name_to_attribute
    queued_lines_attr = parent.panda_name_to_attribute[queued_lines_name]
    assert isinstance(queued_lines_attr, AttrR)
    assert queued_lines_attr.group == WidgetGroup.PARAMETERS.value

    # Verify that CLEAR command was added to parent
    assert hasattr(parent, "clear")
    assert isinstance(parent.clear, Command)
    await parent.clear()
    raw_panda.send.assert_awaited_once_with(str(block_name), [])

    # Verify table io_ref has append support and a NEXT_WRITE reference
    table_attr = parent.panda_name_to_attribute[block_name]
    assert isinstance(table_attr.io_ref, TableFieldIORef)
    assert table_attr.io_ref.next_write_attr is not None
    assert table_attr.io_ref.next_write_attr is next_write_attr
    # Verify append_to_panda is wired to the raw panda append callable.
    assert callable(table_attr.io_ref.append_to_panda)
    assert table_attr.io_ref.append_to_panda is raw_panda.append_to_panda


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
        fields={"field": table_field_details},
        row_words=1,  # Must be > 0 for words_to_table to work
        has_mode=False,
    )

    block_name = PandaName("test_block_no_mode")
    initial_values = {block_name: ["0"]}

    # Create mock table data for panda_value_to_attribute_value
    mock_table_data = np.array([(0,)], dtype=[("field", np.int32)])

    # Patch the low-level conversion to avoid integration complexity
    with patch(
        "fastcs_pandablocks.panda.blocks.blocks.panda_value_to_attribute_value",
        return_value=mock_table_data,
    ):
        # Call the method under test
        block._make_table_field(parent, block_name, table_field_info, initial_values)

    # Verify that no NEXT_WRITE/MODE/QUEUED_LINES attributes were created
    next_write_name = block_name + PandaName(sub_field="NEXT_WRITE")
    assert next_write_name not in parent.panda_name_to_attribute

    mode_name = block_name + PandaName(sub_field="MODE")
    assert mode_name not in parent.panda_name_to_attribute

    queued_lines_name = block_name + PandaName(sub_field="QUEUED_LINES")
    assert queued_lines_name not in parent.panda_name_to_attribute

    # Verify that no clear command was added
    assert not hasattr(parent, "clear")

    # Verify that the table attribute's io_ref has next_write_attr = None
    table_attr = parent.panda_name_to_attribute[block_name]
    assert isinstance(table_attr.io_ref, TableFieldIORef)
    assert table_attr.io_ref.next_write_attr is None
