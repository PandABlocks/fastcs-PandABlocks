from collections.abc import Callable, Coroutine
from typing import Any

from fastcs.attributes import Attribute, AttrR
from fastcs.controllers import Controller, ControllerVector
from fastcs.datatypes import DataType, String

from fastcs_pandablocks.types import PandaName


class BlockControllerVector(ControllerVector):
    """Vector containing numbered panda blocks."""


class BlockController(Controller):
    """Controller for handling a panda block."""

    def __init__(
        self,
        panda_name: PandaName,
        put_value_to_panda: Callable[
            [PandaName, DataType, Any], Coroutine[None, None, None]
        ],
        label: str | None = None,
        ios: list | None = None,
    ):
        self.description = label
        self.panda_name = panda_name
        self.put_value_to_panda = put_value_to_panda

        self.panda_name_to_attribute: dict[PandaName, Attribute] = {}

        super().__init__(ios=ios)

    async def initialise(self):
        if self.description is not None:
            self.add_attribute(
                PandaName("LABEL"),
                AttrR(
                    String(),
                    description="Label from metadata.",
                    initial_value=self.description,
                ),
            )

    def add_attribute(self, name: PandaName, attr: Attribute) -> None:
        self.panda_name_to_attribute[name] = attr
        super().add_attribute(name.attribute_name, attr)
