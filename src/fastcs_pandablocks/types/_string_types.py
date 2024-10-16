from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import TypeVar

T = TypeVar("T")

PANDA_SEPARATOR = "."


def _extract_number_at_end_of_string(string: str) -> tuple[str, int | None]:
    pattern = r"(\D+)(\d+)$"
    match = re.match(pattern, string)
    if match:
        return (match.group(1), int(match.group(2)))
    return string, None


def _format_with_separator(
    separator: str, *sections: tuple[str | None, int | None] | str | None
) -> str:
    result = ""
    for section in sections:
        if isinstance(section, tuple):
            section_string, section_number = section
            if section_string is not None:
                result += f"{separator}{section_string}"
            if section_number is not None:
                result += f"{section_number}"
        elif section is not None:
            result += f"{separator}{section}"

    return result.lstrip(separator)


def _to_python_attribute_name(string: str):
    return string.replace("-", "_").lower()


def _choose_sub_name(sub_pv_1: T, sub_pv_2: T) -> T:
    if sub_pv_1 is not None and sub_pv_2 is not None:
        if sub_pv_1 != sub_pv_2:
            raise TypeError(f"Ambiguous pv elements on add {sub_pv_1} and {sub_pv_2}")
    return sub_pv_2 or sub_pv_1


@dataclass(frozen=True)
class PandaName:
    block: str | None = None
    block_number: int | None = None
    field: str | None = None
    sub_field: str | None = None

    def up_to_block(self) -> PandaName:
        return PandaName(block=self.block, block_number=self.block_number)

    def up_to_field(self) -> PandaName:
        return self.up_to_block() + PandaName(field=self.field)

    @cached_property
    def _string_form(self) -> str:
        return _format_with_separator(
            PANDA_SEPARATOR, (self.block, self.block_number), self.field, self.sub_field
        )

    def __str__(self) -> str:
        return self._string_form

    @classmethod
    def from_string(cls, name: str):
        split_name = name.split(PANDA_SEPARATOR)

        if split_name == [""]:
            return PandaName()

        block, block_number, field, sub_field = None, None, None, None
        block, block_number = _extract_number_at_end_of_string(split_name[0])
        field = split_name[1] if len(split_name) > 1 else None
        sub_field = split_name[2] if len(split_name) > 2 else None

        return PandaName(
            block=block, block_number=block_number, field=field, sub_field=sub_field
        )

    def __add__(self, other: PandaName) -> PandaName:
        return PandaName(
            block=_choose_sub_name(self.block, other.block),
            block_number=_choose_sub_name(self.block_number, other.block_number),
            field=_choose_sub_name(self.field, other.field),
            sub_field=_choose_sub_name(self.sub_field, other.sub_field),
        )

    @cached_property
    def attribute_name(self) -> str:
        if self.sub_field:
            return _to_python_attribute_name(f"{self.field}_{self.sub_field}")
        if self.field:
            return _to_python_attribute_name(self.field)
        if self.block:
            return _to_python_attribute_name(self.block) + (
                f"{self.block_number}" if self.block_number is not None else ""
            )
        return ""

    def __contains__(self, other: PandaName) -> bool:
        for attr in ("block", "block_number", "field", "sub_field"):
            sub_value, super_value = getattr(other, attr), getattr(self, attr)
            if super_value is None:
                break
            if sub_value != super_value:
                return False
        return True
