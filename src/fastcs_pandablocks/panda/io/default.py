from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import (
    AttributeIO,
    AttributeIORef,
    AttrW,
)
from fastcs.datatypes import DataType, DType_T

from fastcs_pandablocks.panda.utils import (
    attribute_value_to_panda_value,
)
from fastcs_pandablocks.types import PandaName


@dataclass
class DefaultFieldIORef(AttributeIORef):
    panda_name: PandaName
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]


class DefaultFieldIO(AttributeIO[DType_T, DefaultFieldIORef]):
    """Default IO for sending and updating introspected attributes."""

    async def send(
        self, attr: AttrW[DType_T, DefaultFieldIORef], value: DType_T
    ) -> None:
        await attr.io_ref.put_value_to_panda(
            attr.io_ref.panda_name,
            attr.datatype,
            attribute_value_to_panda_value(attr.datatype, value),
        )
