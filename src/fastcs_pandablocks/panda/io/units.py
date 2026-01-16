import enum
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import (
    AttributeIO,
    AttributeIORef,
    AttrRW,
    AttrW,
)
from fastcs.datatypes import DataType, Float

from fastcs_pandablocks.panda.utils import (
    attribute_value_to_panda_value,
)
from fastcs_pandablocks.types import PandaName


class TimeUnit(enum.Enum):
    """Enum class for PandA time fields."""

    min = "min"
    s = "s"
    ms = "ms"
    us = "us"


@dataclass
class UnitsIORef(AttributeIORef):
    attribute_to_scale: AttrRW
    current_scale: TimeUnit
    panda_name: PandaName
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]


class UnitsIO(AttributeIO[enum.Enum, UnitsIORef]):
    """A sender for arming and disarming the Pcap."""

    async def send(self, attr: AttrW[enum.Enum, UnitsIORef], value: enum.Enum):
        await attr.io_ref.put_value_to_panda(
            attr.io_ref.panda_name,
            attr.datatype,
            attribute_value_to_panda_value(attr.datatype, value),
        )

        attr.io_ref.attribute_to_scale.update_datatype(Float(units=value.name, prec=5))
