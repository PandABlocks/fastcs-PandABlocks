from enum import Enum as Enum

import numpy as np
import pytest
from fastcs.datatypes import Bool, Float, Int, String, Table
from fastcs.datatypes import Enum as FastcsEnum

from fastcs_pandablocks.panda.utils import (
    attribute_value_to_panda_value,
    panda_value_to_attribute_value,
)


class TestEnum(Enum):
    A = "First"
    B = "Second"


@pytest.mark.parametrize(
    "datatype, panda_value, expected_value",
    [
        (String(), "string", "string"),
        (Int(), "10", 10),
        (Bool(), "1", True),
        (Bool(), "0", False),
        (Float(), "1", 1.0),
        (Float(), "1.5", 1.5),
        (FastcsEnum(enum_cls=TestEnum), "B", TestEnum.B),
        (FastcsEnum(enum_cls=TestEnum), "A", TestEnum.A),
        (
            Table(structured_dtype=[("val1", np.int32), ("val2", np.int32)]),
            {"VAL1": [1, 2, 3], "VAL2": [4, 5, 6]},
            np.array(
                [(1, 4), (2, 5), (3, 6)], dtype=[("val1", np.int32), ("val2", np.int32)]
            ),
        ),
    ],
)
def test_panda_value_to_attribute_value(datatype, panda_value, expected_value):
    """Values from the panda arrive as strings or dicts, and must be converted."""
    result = panda_value_to_attribute_value(datatype, panda_value)
    if isinstance(expected_value, np.ndarray):
        assert np.array_equal(result, expected_value)
    else:
        assert result == expected_value


@pytest.mark.parametrize(
    "datatype, value, expected_panda_value",
    [
        (String(), "string", "string"),
        (Int(), 10, "10"),
        (Bool(), True, "1"),
        (Bool(), False, "0"),
        (Float(), 1.0, "1.0"),
        (Float(), 1.5, "1.5"),
        (FastcsEnum(enum_cls=TestEnum), TestEnum.B, "B"),
        (FastcsEnum(enum_cls=TestEnum), TestEnum.A, "A"),
        (
            Table(structured_dtype=[("val1", np.int32), ("val2", np.int32)]),
            np.array(
                [(1, 4), (2, 5), (3, 6)], dtype=[("val1", np.int32), ("val2", np.int32)]
            ),
            {"VAL1": [1, 2, 3], "VAL2": [4, 5, 6]},
        ),
    ],
)
def test_attribute_value_to_panda_value(datatype, value, expected_panda_value):
    """Attribute values must be converted back into strings or dicts for the panda."""
    result = attribute_value_to_panda_value(datatype, value)
    assert result == expected_panda_value


def test_panda_value_to_attribute_value_fails_if_unkown_datatype():
    with pytest.raises(NotImplementedError, match="Unknown datatype"):
        panda_value_to_attribute_value(object(), "some_value")  # type: ignore


def test_attribute_value_to_panda_value_fails_if_unkown_datatype():
    with pytest.raises(NotImplementedError, match="Unknown datatype"):
        attribute_value_to_panda_value(object(), "some_value")  # type: ignore
