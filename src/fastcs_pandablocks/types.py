from dataclasses import dataclass
import re
from pydantic import BaseModel
from typing import Literal

from pydantic import BaseModel


# Dataclasses for names

@dataclass
class _Name:
    _name: str

    def __str__(self):
        return str(self._name)

class PandaName(_Name):
    def to_epics_name(self):
        return EpicsName(self._name.replace(".", ":"))

class EpicsName(_Name):
    def to_panda_name(self):
        return PandaName(self._name.replace(":", "."))

    def to_pvi_name(self):
        relevant_section = self._name.split(":")[-1]
        words = relevant_section.replace("-", "_").split("_")
        capitalised_word = "".join(word.capitalize() for word in words)

        # We don't want to allow any non-alphanumeric characters.
        formatted_word = re.search(r"[A-Za-z0-9]+", capitalised_word)
        assert formatted_word

        return PviName(formatted_word.group())

class PviName(_Name):
    ...



Field_T = Literal[
    "time",
    "bit_out",
    "pos_out",
    "ext_out",
    "bit_mux",
    "pos_mux",
    "param",
    "read",
    "write",
]

FieldSubtype_T = Literal[
    "timestamp",
    "samples",
    "bits",
    "uint",
    "int",
    "scalar",
    "bit",
    "action",
    "lut",
    "enum",
    "time",
]


class PandaField(BaseModel, frozen=True):
    """Validates fields from the client."""

    field_type: Field_T
    field_subtype: FieldSubtype_T | None


TIME_FIELDS = {
    PandaField(field_type="time", field_subtype=None),
}

BIT_OUT_FIELDS = {
    PandaField(field_type="bit_out", field_subtype=None),
}

POS_OUT_FIELDS = {
    PandaField(field_type="pos_out", field_subtype=None),
}

EXT_OUT_FIELDS = {
    PandaField(field_type="ext_out", field_subtype="timestamp"),
    PandaField(field_type="ext_out", field_subtype="samples"),
}

EXT_OUT_BITS_FIELDS = {
    PandaField(field_type="ext_out", field_subtype="bits"),
}

BIT_MUX_FIELDS = {
    PandaField(field_type="bit_mux", field_subtype=None),
}

POS_MUX_FIELDS = {
    PandaField(field_type="pos_mux", field_subtype=None),
}

UINT_FIELDS = {
    PandaField(field_type="param", field_subtype="uint"),
    PandaField(field_type="read", field_subtype="uint"),
    PandaField(field_type="write", field_subtype="uint"),
}

INT_FIELDS = {
    PandaField(field_type="param", field_subtype="int"),
    PandaField(field_type="read", field_subtype="int"),
    PandaField(field_type="write", field_subtype="int"),
}

SCALAR_FIELDS = {
    PandaField(field_type="param", field_subtype="scalar"),
    PandaField(field_type="read", field_subtype="scalar"),
    PandaField(field_type="write", field_subtype="scalar"),
}

BIT_FIELDS = {
    PandaField(field_type="param", field_subtype="bit"),
    PandaField(field_type="read", field_subtype="bit"),
    PandaField(field_type="write", field_subtype="bit"),
}

ACTION_FIELDS = {
    PandaField(field_type="param", field_subtype="action"),
    PandaField(field_type="read", field_subtype="action"),
    PandaField(field_type="write", field_subtype="action"),
}

