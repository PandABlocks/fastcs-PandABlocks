from __future__ import annotations

from dataclasses import dataclass
import re
from pandablocks.responses import (
    BitMuxFieldInfo,
    BitOutFieldInfo,
    BlockInfo,
    Changes,
    EnumFieldInfo,
    ExtOutBitsFieldInfo,
    ExtOutFieldInfo,
    FieldInfo,
    PosMuxFieldInfo,
    PosOutFieldInfo,
    ScalarFieldInfo,
    SubtypeTimeFieldInfo,
    TableFieldInfo,
    TimeFieldInfo,
    UintFieldInfo,
)
from typing import Union


EPICS_SEPERATOR = ":"
PANDA_SEPERATOR = "."

def _extract_number_at_of_string(string: str) -> tuple[str, int | None]:
        pattern = r"(\D+)(\d+)$"
        print("===================================================")
        print(string)
        match = re.match(pattern, string)
        if match:
            return (match.group(1), int(match.group(2)))
        return string, None


@dataclass(frozen=True)
class _Name:
    _name: str

    def __str__(self):
        return str(self._name)
    def __repr__(self):
        return str(self)

class PandaName(_Name):
    def to_epics_name(self):
        return EpicsName(self._name.replace(PANDA_SEPERATOR, EPICS_SEPERATOR))

class EpicsName(_Name):
    block: str | None = None
    block_number: int | None = None
    field: str | None = None
    field_number: int | None = None
    prefix: str | None = None

    def __init__(
        self,
        prefix=None,
        block: str | None = None,
        block_number: int | None = None,
        field: str | None = None,
        field_number: int | None = None
    ):
        self.prefix = prefix
        self.block = block
        self.block_number = block_number
        self.field = field
        self.field_number = field_number

        prefix_string = f"{self.prefix}{EPICS_SEPERATOR}" if self.prefix is not None else ""
        block_number_string = f"{self.block_number}" if self.block_number is not None else ""
        block_with_number = f"{self.block}{block_number_string}{EPICS_SEPERATOR}" if self.block is not None else ""
        field_number_string = f"{self.field_number}" if self.field_number is not None else ""
        field_with_number = f"{self.field}{field_number_string}" if self.field is not None else ""

        super().__init__(f"{prefix_string}{block_with_number}{field_with_number}")

    def to_panda_name(self):
        return PandaName(self._name.replace(EPICS_SEPERATOR, PANDA_SEPERATOR))

    def to_pvi_name(self):
        relevant_section = self._name.split(EPICS_SEPERATOR)[-1]
        words = relevant_section.replace("-", "_").split("_")
        capitalised_word = "".join(word.capitalize() for word in words)

        # We don't want to allow any non-alphanumeric characters.
        formatted_word = re.search(r"[A-Za-z0-9]+", capitalised_word)
        assert formatted_word

        return PviName(formatted_word.group())
    
    def __add__(self, suffix: "EpicsName"):
        return EpicsName(f"{str(self)}{EPICS_SEPERATOR}{str(suffix)}")




class PviName(_Name):
    ...


ResponseType = Union[
    BitMuxFieldInfo,
    BitOutFieldInfo,
    EnumFieldInfo,
    ExtOutBitsFieldInfo,
    ExtOutFieldInfo,
    FieldInfo,
    PosMuxFieldInfo,
    PosOutFieldInfo,
    ScalarFieldInfo,
    SubtypeTimeFieldInfo,
    TableFieldInfo,
    TimeFieldInfo,
    UintFieldInfo, 
]
