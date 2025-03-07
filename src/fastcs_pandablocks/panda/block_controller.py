from collections.abc import Callable, Coroutine
from typing import Any

from fastcs.attributes import Attribute, AttrR
from fastcs.controller import SubController
from fastcs.datatypes import DataType, String

from fastcs_pandablocks.types import PandaName


class BlockController(SubController):
    def __init__(
        self,
        panda_name: PandaName,
        put_value_to_panda: Callable[
            [PandaName, DataType, Any], Coroutine[None, None, None]
        ],
        label: str | None = None,
    ):
        self.description = label
        self.panda_name = panda_name
        self.put_value_to_panda = put_value_to_panda

        self.attributes: dict[str, Attribute] = {}
        self.panda_name_to_attribute: dict[PandaName, Attribute] = {}

        if self.description is not None:
            self.attributes["LABEL"] = AttrR(
                String(),
                description="Label from metadata.",
                initial_value=self.description,
            )

        super().__init__()

    def add_attribute(self, panda_name: PandaName, attribute: Attribute) -> None:
        self.attributes[panda_name.attribute_name] = attribute
        self.panda_name_to_attribute[panda_name] = attribute
