from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

EPICS_SEPERATOR = ":"
PANDA_SEPERATOR = "."


def _extract_number_at_of_string(string: str) -> tuple[str, int | None]:
    pattern = r"(\D+)(\d+)$"
    match = re.match(pattern, string)
    if match:
        return (match.group(1), int(match.group(2)))
    return string, None


def _format_with_seperator(
    seperator: str, *sections: tuple[str | None, int | None] | str | None
) -> str:
    result = ""
    for section in sections:
        if isinstance(section, tuple):
            section_string, section_number = section
            if section_string is not None:
                result += f"{seperator}{section_string}"
            if section_number is not None:
                result += f"{section_number}"
        elif section is not None:
            result += f"{seperator}{section}"

    return result.lstrip(seperator)


@dataclass(frozen=True)
class _Name:
    _name: str

    def __str__(self):
        return str(self._name)

    def __repr__(self):
        return str(self)


class PandaName(_Name):
    def __init__(
        self,
        block: str | None = None,
        block_number: int | None = None,
        field: str | None = None,
        sub_field: str | None = None,
    ):
        self.block = block
        self.block_number = block_number
        self.field = field
        self.sub_field = sub_field

        super().__init__(
            _format_with_seperator(
                PANDA_SEPERATOR, (block, block_number), field, sub_field
            )
        )

    @classmethod
    def from_string(cls, name: str):
        split_name = name.split(PANDA_SEPERATOR)

        block, block_number = _extract_number_at_of_string(split_name[0])
        field = split_name[1]
        sub_field = split_name[2] if len(split_name) == 3 else None

        return PandaName(
            block=block, block_number=block_number, field=field, sub_field=sub_field
        )

    def to_epics_name(self):
        return EpicsName(
            block=self.block,
            block_number=self.block_number,
            field=self.field,
            sub_field=self.sub_field,
        )


class EpicsName(_Name):
    def __init__(
        self,
        *,
        prefix: str | None = None,
        block: str | None = None,
        block_number: int | None = None,
        field: str | None = None,
        sub_field: str | None = None,
    ):
        assert block_number != 0

        self.prefix = prefix
        self.block = block
        self.block_number = block_number
        self.field = field
        self.sub_field = sub_field

        super().__init__(
            _format_with_seperator(
                EPICS_SEPERATOR, prefix, (block, block_number), field
            )
        )

    @classmethod
    def from_string(cls, name: str) -> EpicsName:
        """Converts a string to an EPICS name, must contain a prefix."""
        split_name = name.split(EPICS_SEPERATOR)
        if len(split_name) < 3:
            raise ValueError(
                f"Received a a pv string `{name}` which isn't of the form "
                "`PREFIX:BLOCK:FIELD` or `PREFIX:BLOCK:FIELD:SUB_FIELD`."
            )
        split_name = name.split(EPICS_SEPERATOR)
        prefix, block_with_number, field = split_name[:3]
        block, block_number = _extract_number_at_of_string(block_with_number)
        sub_field = split_name[3] if len(split_name) == 4 else None

        return EpicsName(
            prefix=prefix,
            block=block,
            block_number=block_number,
            field=field,
            sub_field=sub_field,
        )

    def to_panda_name(self) -> PandaName:
        return PandaName(
            block=self.block,
            block_number=self.block_number,
            field=self.field,
            sub_field=self.sub_field,
        )

    def to_pvi_name(self) -> PviName:
        assert self.field
        words = self.field.replace("-", "_").split("_")
        capitalised_word = "".join(word.capitalize() for word in words)

        # We don't want to allow any non-alphanumeric characters.
        formatted_word = re.search(r"[A-Za-z0-9]+", capitalised_word)
        assert formatted_word

        return PviName(formatted_word.group())

    def __add__(self, other: EpicsName) -> EpicsName:
        """
        Returns the sum of PVs:

        EpicsName(prefix="PREFIX", block="BLOCK") + EpicsName(field="FIELD")
        == EpicsName.from_string("PREFIX:BLOCK:FIELD")
        """

        def _choose_sub_pv(sub_pv_1: T, sub_pv_2: T) -> T:
            if sub_pv_1 is not None and sub_pv_2 is not None:
                if sub_pv_1 != sub_pv_2:
                    raise TypeError(
                        "Ambiguous pv elements on `EpicsName` add "
                        f"{sub_pv_1} and {sub_pv_2}"
                    )
            return sub_pv_2 or sub_pv_1

        return EpicsName(
            prefix=_choose_sub_pv(self.prefix, other.prefix),
            block=_choose_sub_pv(self.block, other.block),
            block_number=_choose_sub_pv(self.block_number, other.block_number),
            field=_choose_sub_pv(self.field, other.field),
            sub_field=_choose_sub_pv(self.sub_field, other.sub_field),
        )

    def __contains__(self, other: EpicsName) -> bool:
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
            _check_eq(self.prefix, other.prefix)
            and _check_eq(self.block, other.block)
            and _check_eq(self.block_number, other.block_number)
            and _check_eq(self.field, other.field)
            and _check_eq(self.sub_field, other.sub_field)
        )


class PviName(_Name):
    pass
