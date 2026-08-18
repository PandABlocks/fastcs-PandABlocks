from unittest.mock import AsyncMock, MagicMock

import pytest

from fastcs_pandablocks.panda.panda_controller import PandaController


@pytest.fixture
def controller():
    return PandaController(MagicMock())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "block_name, should_register",
    [
        pytest.param("fmc_in", True, id="letters_and_underscore"),
        pytest.param("PULSE", True, id="all_letters"),
        pytest.param("COUNTER1", False, id="numerically_indexed"),
        pytest.param("TTLIN12", False, id="multi_digit_index"),
        pytest.param("FMC_OUT", True, id="uppercase_with_underscore"),
    ],
)
async def test_initialise_registers_correct_blocks(
    controller, block_name, should_register
):
    """Only non-numerically-indexed block names (e.g. "fmc_in")
    should be registered as sub controllers. Numerically indexed names
    (e.g. "counter1") are registered via their ControllerVector instead
    and must be skipped here."""

    mock_block = MagicMock()
    mock_block.initialise = AsyncMock()

    controller.connect = AsyncMock()
    controller.add_sub_controller = MagicMock()
    controller._blocks.controllers = MagicMock(return_value=[(block_name, mock_block)])

    await controller.initialise()

    if should_register:
        controller.add_sub_controller.assert_called_once_with(
            block_name.lower(), mock_block
        )
        mock_block.initialise.assert_awaited_once()
    else:
        controller.add_sub_controller.assert_not_called()
        mock_block.initialise.assert_not_awaited()
