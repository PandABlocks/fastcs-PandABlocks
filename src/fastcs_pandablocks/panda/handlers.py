import asyncio
import enum
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

import numpy as np
from fastcs.attribute_io import AttributeIO, AttributeIORef
from fastcs.attributes import (
    AttrRW,
    AttrW,
)
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T, Table
from pandablocks.responses import TableFieldInfo
from pandablocks.utils import table_to_words

from fastcs_pandablocks.types import PandaName


def panda_value_to_attribute_value(
    fastcs_datatype: DataType[T], value: str | dict
) -> T:
    """Converts from a value received from the panda to the attribute value."""

    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return bool(int(value))
        case Int() | Float():
            return fastcs_datatype.dtype(value)
        case Enum():
            return fastcs_datatype.enum_cls[value]
        case Table():
            num_rows = len(next(iter(value.values())))
            structured_datatype = fastcs_datatype.structured_dtype
            attribute_value = np.zeros(num_rows, fastcs_datatype.structured_dtype)
            for field_name, _ in structured_datatype:
                attribute_value[field_name] = value[field_name]
            return attribute_value

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


def attribute_value_to_panda_value(
    fastcs_datatype: DataType[T], value: T
) -> str | dict:
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
                panda_value[field_name] = value[field_name].tolist()
            return panda_value
        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


@dataclass
class DefaultFieldHandlerIORef(AttributeIORef):
    panda_name: PandaName
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]


class DefaultFieldHandlerIO(AttributeIO[T, DefaultFieldHandlerIORef]):
    """Default handler for sending and updating introspected attributes."""

    async def send(self, attr: AttrW[T, DefaultFieldHandlerIORef], value: T) -> None:
        await attr.io_ref.put_value_to_panda(
            attr.io_ref.panda_name,
            attr.datatype,
            attribute_value_to_panda_value(attr.datatype, value),
        )


@dataclass
class TableFieldHandlerIORef(AttributeIORef):
    panda_name: PandaName
    field_info: TableFieldInfo
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]


class TableFieldHandlerIO(AttributeIO[T, TableFieldHandlerIORef]):
    """A handler for updating Table valued attributes."""

    async def send(self, attr: AttrW[T, TableFieldHandlerIORef], value: T) -> None:
        attr_value = attribute_value_to_panda_value(attr.datatype, value)
        assert isinstance(attr_value, dict)
        panda_words = table_to_words(attr_value, attr.io_ref.field_info)
        await attr.io_ref.put_value_to_panda(
            attr.io_ref.panda_name, attr.datatype, panda_words
        )


async def _set_attr_if_not_already_value(attribute: AttrRW[T], value: T):
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


class ArmCommand(enum.Enum):
    DISARM = "Disarm"
    ARM = "Arm"


@dataclass
class ArmIORef(AttributeIORef):
    arm: Callable[[], Coroutine[None, None, None]]
    disarm: Callable[[], Coroutine[None, None, None]]


class ArmIO(AttributeIO[T, ArmIORef]):
    """A sender for arming and disarming the Pcap."""

    async def send(self, attr: AttrW[T, ArmIORef], value: Any):
        if value is ArmCommand.ARM:
            logging.info("Arming PandA.")
            await attr.io_ref.arm()
        else:
            logging.info("Disarming PandA.")
            await attr.io_ref.disarm()
