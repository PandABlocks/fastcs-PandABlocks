import pytest
from fastcs_pandablocks.types import EpicsName


def test_epics_name():
    name1 = EpicsName.from_string("prefix:block1:field1")
    assert name1.prefix == "prefix"
    assert name1.block == "block"
    assert name1.block_number == 1
    assert name1.field == "field"
    assert name1.field_number == 1

def test_epics_name_add():
    assert (
        (EpicsName.from_string("prefix:block1:field1") + EpicsName.from_string("prefix:block1:field1"))
     == EpicsName.from_string("prefix:block1:field1")
    )
    assert EpicsName(block="block") + EpicsName(block_number=1) == EpicsName(block="block", block_number=1)

def test_malformed_epics_name_add():
    pass

def test_epics_name_contains():
    parent_name = EpicsName.from_string("prefix:block1:field1")
    assert EpicsName(block="block") in parent_name
    assert EpicsName(block="block", field_number=1) in parent_name

def test_malformed_epics_name_contains():
    pass
