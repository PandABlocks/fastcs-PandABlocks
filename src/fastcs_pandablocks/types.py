from __future__ import annotations
from fastcs.attributes import AttrR

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
from typing import Union, TypeVar

T = TypeVar("T")

EPICS_SEPERATOR = ":"
PANDA_SEPERATOR = "."

def _extract_number_at_of_string(string: str) -> tuple[str, int | None]:
        pattern = r"(\D+)(\d+)$"
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
    block: str | None = None
    block_number: int | None = None
    field: str | None = None
    field_number: int | None = None

    def __init__(
        self,
        block: str | None = None,
        block_number: int | None = None,
        field: str | None = None,
        field_number: int | None = None,
    ):
        self.block=block 
        self.block_number=block_number
        self.field=field
        self.field_number=field_number
        super().__init__(f"{self.block}{self.block_number}{PANDA_SEPERATOR}{self.field}")
    
    @classmethod
    def from_string(cls, name: str):
        split_name = name.split(PANDA_SEPERATOR)
        assert len(split_name) == 2
        block, block_number = _extract_number_at_of_string(split_name[0])
        field, field_number = _extract_number_at_of_string(split_name[1])
        return PandaName(
            block=block, block_number=block_number, field=field, field_number=field_number
        )

    def to_epics_name(self):
        split_panda_name = self._name.split(PANDA_SEPERATOR)
        return EpicsName(
            block=self.block, block_number=self.block_number, field=self.field, field_number=self.field_number
        )

class EpicsName(_Name):
    prefix: str | None = None
    block: str | None = None
    block_number: int | None = None
    field: str | None = None
    field_number: int | None = None

    def __init__(
        self,
        *,
        prefix: str | None = None,
        block: str | None = None,
        block_number: int | None = None,
        field: str | None = None,
        field_number: int | None = None
    ):
        assert block_number != 0 or field_number != 0

        self.prefix = prefix
        self.block = block
        self.block_number = block_number
        self.field = field
        self.field_number = field_number

        prefix_string = f"{self.prefix}{EPICS_SEPERATOR}" if self.prefix is not None else ""
        block_with_number = f"{self.block}{self.block_number or ''}{EPICS_SEPERATOR}" if self.block is not None else ""
        field_with_number = f"{self.field}{self.field_number or ''}" if self.field is not None else ""

        super().__init__(f"{prefix_string}{block_with_number}{field_with_number}")
    
    @classmethod
    def from_string(cls, name: str):
        """Converts a string to an EPICS name, must contain a prefix."""
        split_name = name.split(EPICS_SEPERATOR)
        assert len(split_name) == 3
        prefix, block_with_number, field_with_number = name.split(EPICS_SEPERATOR)
        block, block_number = _extract_number_at_of_string(block_with_number)
        field, field_number = _extract_number_at_of_string(field_with_number)
        return EpicsName(
            prefix=prefix, block=block, block_number=block_number, field=field, field_number=field_number
        )

    def to_panda_name(self):
        return PandaName.from_string(self._name.replace(EPICS_SEPERATOR, PANDA_SEPERATOR))

    def to_pvi_name(self):
        relevant_section = self._name.split(EPICS_SEPERATOR)[-1]
        words = relevant_section.replace("-", "_").split("_")
        capitalised_word = "".join(word.capitalize() for word in words)

        # We don't want to allow any non-alphanumeric characters.
        formatted_word = re.search(r"[A-Za-z0-9]+", capitalised_word)
        assert formatted_word

        return PviName(formatted_word.group())
    
    def __add__(self, other: EpicsName):
        def _merge_sub_pv(
            sub_pv_1: T, sub_pv_2: T
        ) -> T:
            if sub_pv_1 is not None and sub_pv_2 is not None:
                assert sub_pv_1 == sub_pv_2
            return sub_pv_2 or sub_pv_1

        return EpicsName(
            prefix = _merge_sub_pv(self.prefix, other.prefix),
            block = _merge_sub_pv(self.block, other.block),
            block_number = _merge_sub_pv(self.block_number, other.block_number),
            field = _merge_sub_pv(self.field, other.field),
            field_number = _merge_sub_pv(self.field_number, other.field_number)
        )

    def __contains__(self, other: EpicsName):
        """Checks to see if a given epics name is a subset of another one.
        
        Examples
        --------

        (EpicsName(block="field1") in EpicsName("prefix:block1:field1")) == True
        (EpicsName(block="field1") in EpicsName("prefix:block1:field2")) == False
        """
        def _check_eq(sub_pv_1: T, sub_pv_2: T) -> bool:
            if sub_pv_1 is not None and sub_pv_2 is not None:
                return sub_pv_1 == sub_pv_2
            return True

        return (
            _check_eq(self.prefix, other.prefix) and
            _check_eq(self.block, other.block) and 
            _check_eq(self.block_number, other.block_number) and
            _check_eq(self.field, other.field) and
            _check_eq(self.field_number, other.field_number)
        )





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
