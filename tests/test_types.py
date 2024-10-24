from dataclasses import FrozenInstanceError

import pytest

from fastcs_pandablocks.types import EpicsName, PandaName


@pytest.mark.parametrize(
    "name_factory",
    [
        lambda: EpicsName.from_string("PREFIX:BLOCK:FIELD"),
        lambda: PandaName.from_string("BLOCK.FIELD"),
    ],
)
def test_names_are_frozen(name_factory):
    name = name_factory()
    with pytest.raises(FrozenInstanceError):
        name.block = "hello"


def test_epics_name():
    string_form = "prefix:block1:field:sub_field"
    name1 = EpicsName.from_string(string_form)
    assert name1.prefix == "prefix"
    assert name1.block == "block"
    assert name1.block_number == 1
    assert name1.field == "field"
    assert name1.sub_field == "sub_field"
    assert str(name1) == string_form
    assert name1 == EpicsName(
        prefix="prefix",
        block="block",
        block_number=1,
        field="field",
        sub_field="sub_field",
    )


def test_epics_name_add():
    assert (
        EpicsName.from_string("prefix:block1:field")
        + EpicsName.from_string("prefix:block1:field")
    ) == EpicsName.from_string("prefix:block1:field")
    assert EpicsName(block="block") + EpicsName(block_number=1) == EpicsName(
        block="block", block_number=1
    )
    with pytest.raises(TypeError) as error:
        _ = EpicsName(block="block", block_number=1, field="field") + EpicsName(
            block="block", block_number=2, field="field"
        )
    assert str(error.value) == "Ambiguous pv elements on add 1 and 2"


def test_epics_name_contains():
    parent_name = EpicsName(prefix="prefix", block="block")
    assert parent_name in parent_name
    assert EpicsName(prefix="prefix", block="block", block_number=1) in parent_name
    assert (
        EpicsName(prefix="prefix", block="block", block_number=1, field="field")
        in parent_name
    )
    assert parent_name not in EpicsName(block="block", block_number=1)
    assert parent_name not in EpicsName(prefix="prefix", block="block", block_number=2)
    assert parent_name not in EpicsName(
        prefix="prefix", block="block", block_number=1, field="field"
    )
