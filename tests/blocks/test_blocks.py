from dataclasses import dataclass, field
from unittest.mock import MagicMock

from fastcs.attributes import AttrRW
from fastcs.datatypes import Bool

from fastcs_pandablocks.panda.blocks import BlockController, Blocks
from fastcs_pandablocks.types import PandaName


@dataclass
class FakeController(BlockController):
    """A minimal stand-in for the real introspected-controller type"""

    panda_name_to_attribute: dict = field(default_factory=dict)


def test_get_attribute_returns_known_block():
    """A known block should be returned"""
    blocks = Blocks(MagicMock(), [])

    known_block_attribute = AttrRW(Bool())

    known_block_name = PandaName.from_string("SEQ1.ENABLE").up_to_block()
    mock_controller = FakeController({known_block_name: known_block_attribute})

    blocks._introspected_controllers = {known_block_name: mock_controller}

    assert blocks.get_attribute(known_block_name) is known_block_attribute


def test_get_attribute_returns_none_for_unknown_block():
    """Pseudo-fields (like *METADATA) have no introspected
    controller, so get_attribute should return None."""
    blocks = Blocks(MagicMock(), [])
    panda_name = PandaName.from_string("*METADATA.LAYOUT")

    assert blocks.get_attribute(panda_name) is None


def test_get_attribute_returns_none_for_unknown_field_on_known_block():
    """A known block but an unrecognised field on it should also
    return None."""
    blocks = Blocks(MagicMock(), [])

    known_block_name = PandaName.from_string("PULSE1.WIDTH").up_to_block()
    mock_controller = FakeController()

    blocks._introspected_controllers = {known_block_name: mock_controller}

    panda_name = PandaName.from_string("PULSE1.UNKNOWN_FIELD")

    assert blocks.get_attribute(panda_name) is None
