import pickle
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.blocks.block_controller import (
    BlockController,
    BlockControllerVector,
)
from fastcs_pandablocks.panda.panda_controller import PandaController
from fastcs_pandablocks.types import PandaName

INTROSPECTED_DATA = Path(__file__).parent / "panda_introspection.pkl"


@pytest.fixture
def mock_panda_controller() -> PandaController:
    panda_controller = PandaController(MagicMock())
    panda_controller._ios = []
    raw_panda = mock_raw_panda()
    panda_controller._raw_panda = raw_panda
    panda_controller._blocks = Blocks(raw_panda, ios=[])
    return panda_controller


def mock_raw_panda():
    raw_panda = MagicMock()
    with open(INTROSPECTED_DATA, "rb") as f:
        introspected_data = pickle.load(f)
        raw_panda.introspect = AsyncMock(return_value=introspected_data)
    raw_panda.get = AsyncMock(return_value="MockVersion")
    raw_panda.connect = AsyncMock()
    return raw_panda


EXPECTED_SINGULAR_BLOCKS = {
    "bits",
    "fmc_in",
    "fmc_out",
    "pcap",
    "sfp3_sync_in",
    "sfp3_sync_out",
    "system",
}

EXPECTED_NUMBERED_BLOCKS = {
    "calc": 2,
    "clock": 2,
    "counter": 8,
    "div": 2,
    "filter": 2,
    "inenc": 4,
    "lut": 8,
    "lvdsin": 2,
    "lvdsout": 2,
    "outenc": 4,
    "pcomp": 2,
    "pulse": 4,
    "seq": 2,
    "srgate": 4,
    "ttlin": 6,
    "ttlout": 10,
}


@pytest.mark.asyncio
async def test_block_introspection(mock_panda_controller: PandaController):
    panda_controller = mock_panda_controller
    await panda_controller.initialise()

    all_controllers = panda_controller.sub_controllers
    single_controllers = {
        block_name: block
        for block_name, block in all_controllers.items()
        if isinstance(block, BlockController)
    }
    vector_controllers = {
        block_name: block
        for block_name, block in all_controllers.items()
        if isinstance(block, BlockControllerVector)
    }
    assert "versions" in all_controllers
    assert "data" in all_controllers

    arm_attribute = panda_controller._blocks.get_attribute(
        PandaName.from_string("PCAP") + PandaName(field="Arm")
    )
    assert arm_attribute is not None

    assert len(single_controllers) == len(EXPECTED_SINGULAR_BLOCKS)
    for name in EXPECTED_SINGULAR_BLOCKS:
        assert name in single_controllers

    assert len(vector_controllers) == len(EXPECTED_NUMBERED_BLOCKS)
    for name in EXPECTED_NUMBERED_BLOCKS:
        assert name in vector_controllers
