import asyncio
import enum
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import (
    AttrRW,
)
from fastcs.datatypes import DType_T, Enum


async def _set_attr_if_not_already_value(attribute: AttrRW[DType_T], value: DType_T):
    if attribute.get() != value:
        await attribute.update(value)


@dataclass
class BitGroupOnUpdate:
    """Bits are tied together in bit groups so that when one is set for capture,
    they all are.

    This callback sets all capture attributes in the group when one of them is set.
    """

    capture_attribute: AttrRW[enum.Enum]
    bit_attributes: list[AttrRW[bool]]

    async def __call__(self, value: Any):
        if isinstance(value, enum.Enum):
            bool_value = bool(self.capture_attribute.datatype.index_of(value))  # type: ignore
            enum_value = value
        else:
            bool_value = value
            assert isinstance(self.capture_attribute.datatype, Enum)
            enum_value = self.capture_attribute.datatype.members[int(value)]

        await asyncio.gather(
            *[
                _set_attr_if_not_already_value(bit_attr, bool_value)
                for bit_attr in self.bit_attributes
            ],
            _set_attr_if_not_already_value(self.capture_attribute, enum_value),
        )
