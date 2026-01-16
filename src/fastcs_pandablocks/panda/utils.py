from typing import Any

import numpy as np
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, Table


def panda_value_to_attribute_value(fastcs_datatype: DataType, value: str | dict) -> Any:
    """Converts from a value received from the panda to the attribute value."""

    match fastcs_datatype:
        case String():
            return fastcs_datatype.validate(value)
        case Bool():
            assert isinstance(value, str)
            return fastcs_datatype.validate(int(value))
        case Int() | Float():
            return fastcs_datatype.validate(value)
        case Enum():
            return fastcs_datatype.enum_cls[value]  # type: ignore
        case Table():
            assert isinstance(value, dict)
            num_rows = len(next(iter(value.values())))
            structured_datatype = fastcs_datatype.structured_dtype
            attribute_value = np.zeros(num_rows, fastcs_datatype.structured_dtype)
            for field_name, _ in structured_datatype:
                attribute_value[field_name] = value[field_name.upper()]
            return attribute_value

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


def attribute_value_to_panda_value(fastcs_datatype: DataType, value: Any) -> str | dict:
    """Converts from an attribute value to a value that can be sent to the panda."""

    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return str(int(value))
        case Int() | Float():
            return str(value)
        case Enum():
            return value.name
        case Table():
            assert isinstance(value, np.ndarray)
            panda_value = {}
            for field_name, _ in fastcs_datatype.structured_dtype:
                panda_value[field_name.upper()] = value[field_name].tolist()
            return panda_value
        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")
