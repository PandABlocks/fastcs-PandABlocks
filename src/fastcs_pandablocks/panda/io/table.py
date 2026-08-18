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
from fastcs.datatypes import DataType, DType_T
from pandablocks.responses import TableFieldInfo
from pandablocks.utils import table_to_words

from fastcs_pandablocks.panda.utils import (
    attribute_value_to_panda_value,
)
from fastcs_pandablocks.types import PandaName


class NextWrite(enum.Enum):
    REPLACE = "Replace"
    APPEND = "Append"
    APPEND_LAST = "Append Last"


class Mode(enum.Enum):
    INIT = "INIT"
    FIXED = "FIXED"
    STREAMING = "STREAMING"
    STREAMING_LAST = "STREAMING_LAST"


@dataclass
class TableFieldIORef(AttributeIORef):
    panda_name: PandaName
    field_info: TableFieldInfo
    put_value_to_panda: Callable[
        [PandaName, DataType, Any], Coroutine[None, None, None]
    ]
    append_to_panda: Callable[
        [PandaName, DataType, Any, bool], Coroutine[None, None, None]
    ]
    # Local NEXT_WRITE state carrier created in _make_table_field. Must be an
    # AttrRW (not a plain AttrW) so its last-written value is readable via .get().
    next_write_attr: AttrRW[Any, Any] | None


class TableFieldIO(AttributeIO[DType_T, TableFieldIORef]):
    """An IO for updating Table valued attributes."""

    async def send(self, attr: AttrW[DType_T, TableFieldIORef], value: DType_T) -> None:
        attr_value = attribute_value_to_panda_value(attr.datatype, value)
        assert isinstance(attr_value, dict)
        panda_words = table_to_words(attr_value, attr.io_ref.field_info)

        # If this is a has_mode table, dispatch based on NEXT_WRITE value
        if attr.io_ref.next_write_attr is not None:
            next_write = (
                attr.io_ref.next_write_attr.get()
            )  # read the local NEXT_WRITE value
            match next_write:
                case NextWrite.REPLACE:
                    await attr.io_ref.put_value_to_panda(
                        attr.io_ref.panda_name, attr.datatype, panda_words
                    )
                case NextWrite.APPEND:
                    await attr.io_ref.append_to_panda(
                        attr.io_ref.panda_name, attr.datatype, panda_words, False
                    )
                case NextWrite.APPEND_LAST:
                    await attr.io_ref.append_to_panda(
                        attr.io_ref.panda_name, attr.datatype, panda_words, True
                    )
                case _:
                    # Avoid dropped writes: unknown/unset values default to replace.
                    await attr.io_ref.put_value_to_panda(
                        attr.io_ref.panda_name, attr.datatype, panda_words
                    )
        else:
            # Non-has_mode tables always use Put (replace)
            await attr.io_ref.put_value_to_panda(
                attr.io_ref.panda_name, attr.datatype, panda_words
            )
