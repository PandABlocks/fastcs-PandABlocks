from fastcs_pandablocks.types import PandaName


def test_name():
    name = PandaName.from_string("test1")
    assert name == PandaName(block="test", block_number=1)
    assert name.attribute_name == "test1"

    name = PandaName.from_string("a1.b.c")
    assert name.block == "a"
    assert name.block_number == 1
    assert name.field == "b"
    assert name.sub_field == "c"
    assert name.attribute_name == "b_c"
    assert str(name) == "a1.b.c"

    assert name.up_to_block() == PandaName.from_string("a1")
    assert name.up_to_field() == PandaName.from_string("a1.b")


def test_add():
    block_only_name = PandaName.from_string("a1")
    field_only_name = PandaName(field="b")
    sub_field_only_name = PandaName(sub_field="c")

    block_field_name = block_only_name + field_only_name
    assert str(block_field_name) == "a1.b"
    assert str(block_field_name + sub_field_only_name) == "a1.b.c"


def test_contains():
    name1 = PandaName.from_string("a1.b.c")
    name2 = PandaName.from_string("a1.b")
    name3 = PandaName.from_string("a1")

    assert name1 in name3 and name2 in name3
    assert name3 not in name1 and name3 not in name2
    assert name1 in name2 and name2 not in name1
    assert name1 in name1
