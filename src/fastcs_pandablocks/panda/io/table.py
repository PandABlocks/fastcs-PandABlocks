from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import (
    AttributeIO,
    AttributeIORef,
    AttrW,
)
from fastcs.datatypes import DataType, DType_T
from pandablocks.responses import TableFieldInfo
from pandablocks.utils import table_to_words

from fastcs_pandablocks.panda.utils import (
    attribute_value_to_panda_value,
)
from fastcs_pandablocks.types import PandaName


@dataclass
class TableFieldIORef(AttributeIORef):
    panda_name: PandaName
    field_info: TableFieldInfo
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]


class TableFieldIO(AttributeIO[DType_T, TableFieldIORef]):
    """An IO for updating Table valued attributes."""

    async def send(self, attr: AttrW[DType_T, TableFieldIORef], value: DType_T) -> None:
        attr_value = attribute_value_to_panda_value(attr.datatype, value)
        assert isinstance(attr_value, dict)
        panda_words = table_to_words(attr_value, attr.io_ref.field_info)
        await attr.io_ref.put_value_to_panda(
            attr.io_ref.panda_name, attr.datatype, panda_words
        )
