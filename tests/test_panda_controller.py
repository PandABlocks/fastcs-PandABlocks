from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastcs.attributes import AttrR
from fastcs.datatypes import Int

from fastcs_pandablocks.panda.panda_controller import PandaController
from fastcs_pandablocks.types import PandaName


@pytest.fixture
def panda_name():
    return PandaName.from_string("PULSE1.WIDTH")


@pytest.fixture
def controller():
    return PandaController(MagicMock())


@pytest.mark.asyncio
async def test_update_field_value_gets_attribute_and_updates(controller, panda_name):
    """A panda name's attribute should be updated with coerced value."""
    attribute = AttrR(Int())
    controller._blocks.get_attribute = MagicMock(return_value=attribute)

    await controller.update_field_value(panda_name, "10")

    assert attribute.get() == 10


@pytest.mark.asyncio
async def test_update_field_value_logs_and_skips_on_coerce_failure(
    controller, panda_name
):
    """A ValueError from coercion should be caught and logged, not raised."""
    attribute = AttrR(Int())
    controller._blocks.get_attribute = MagicMock(return_value=attribute)

    with patch("fastcs_pandablocks.panda.panda_controller.logger") as mock_logger:
        await controller.update_field_value(panda_name, "not_an_int")

    mock_logger.opt.assert_called_once_with(exception=True)
    mock_logger.opt.return_value.error.assert_called_once_with("Coerce failed")


@pytest.mark.asyncio
async def test_update_field_value_logs_and_skips_on_failed_field_lookup(
    controller, panda_name
):
    """An error from a missing field should be caught and logged, not raised."""
    controller._blocks.get_attribute = MagicMock(return_value=None)

    with patch("fastcs_pandablocks.panda.panda_controller.logger") as mock_logger:
        await controller.update_field_value(panda_name, "1")

    mock_logger.opt.assert_called_once_with(exception=True)
    mock_logger.opt.return_value.error.assert_called_once_with(
        f"Couldn't find panda field for {panda_name}."
    )


@pytest.mark.asyncio
async def test_update_all_fields_succeed_no_error(controller):
    """Happy path: all fields update cleanly, no exception raised."""
    controller._raw_panda.get_changes = AsyncMock(
        return_value={
            "PULSE1.WIDTH": "42",
            "PULSE2.WIDTH": "10",
        }
    )
    controller.update_field_value = AsyncMock(return_value=None)

    await controller.update()

    assert controller.update_field_value.await_count == 2


@pytest.mark.asyncio
async def test_update_logs_but_does_not_raise_on_single_field_failure(controller):
    """One bad field (e.g. *METADATA producing an unexpected exception
    somewhere downstream) should be logged, but must not prevent other
    fields updating or kill the scan task."""
    controller._raw_panda.get_changes = AsyncMock(
        return_value={
            "*METADATA.LAYOUT": "some layout",
            "PULSE1.WIDTH": "42",
        }
    )

    async def fake_update_field_value(panda_name, value):
        if str(panda_name).startswith("*METADATA"):
            raise RuntimeError("Some Exception")

    controller.update_field_value = AsyncMock(side_effect=fake_update_field_value)

    with patch("fastcs_pandablocks.panda.panda_controller.logger") as mock_logger:
        await controller.update()

    # Both fields were attempted.
    assert controller.update_field_value.await_count == 2

    # Pull out the actual exception passed and check its type/message
    exception = mock_logger.opt.call_args.kwargs["exception"]
    assert isinstance(exception, RuntimeError)
    assert str(exception) == "Some Exception"

    # Assert chained .error() call on opt() return
    mock_logger.opt.return_value.error.assert_called_once_with(
        "Failed to update field *METADATA.LAYOUT"
    )


@pytest.mark.asyncio
async def test_update_raises_runtime_error_when_get_changes_fails(controller):
    """A failure fetching changes from the PandA itself should still
    surface as a RuntimeError (this is a connection-level failure,
    not a per-field one)."""
    controller._raw_panda.get_changes = AsyncMock(
        side_effect=ConnectionError("disconnected")
    )
    with pytest.raises(RuntimeError, match="Failed to update changes"):
        await controller.update()
