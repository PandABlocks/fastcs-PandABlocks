import asyncio
import logging
from typing import Any

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import Controller
from fastcs.cs_methods import Scan
from fastcs.datatypes import Table
from pandablocks.utils import words_to_table

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.panda.handlers import (
    TableFieldHandler,
    panda_value_to_attribute_value,
)
from fastcs_pandablocks.types import PandaName

LOGGER = logging.getLogger(__name__)


class PandaController(Controller):
    """Controller for polling data from the panda through pandablocks-client.

    Changes are received at a given poll period and passed to sub-controllers.
    """

    def __init__(self, hostname: str, poll_period: float) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62
        super().__init__()

        self.attributes: dict[str, Attribute] = {}
        self._raw_panda = RawPanda(hostname)
        self._blocks: Blocks = Blocks(self._raw_panda)
        self.update = Scan(self._update, poll_period)

        self.connected = False

    async def connect(self) -> None:
        if self.connected:
            # `connect` needs to be called in `initialise`,
            # then FastCS will attempt to call it again.
            return
        await self._raw_panda.connect()
        await self._blocks.parse_introspected_data()
        await self._blocks.setup_post_introspection()
        self.connected = True

    async def initialise(self) -> None:
        await self.connect()
        for block_name, block in self._blocks.controllers():
            self.register_sub_controller(block_name, block)

    async def update_field_value(self, panda_name: PandaName, value: str | list[str]):
        """Update a panda field with either a single value or a list of words."""

        attribute = self._blocks.get_attribute(panda_name)
        if attribute is None:
            LOGGER.error(f"Couldn't find panda field for {panda_name}.")
            return

        try:
            attribute_value = self._coerce_value_to_panda_type(attribute, value)
        except ValueError as e:
            LOGGER.error(str(e))
            return

        await self.update_attribute(attribute, attribute_value)

    def _coerce_value_to_panda_type(
        self, attribute: Attribute, value: str | list[str]
    ) -> Any:
        """Convert a provided value into an attribute_value for this panda attribute."""
        match value:
            case list() as words:
                if not isinstance(attribute.datatype, Table):
                    raise ValueError(f"{attribute} is not a Table attribute")
                sender = getattr(attribute, "sender", None)
                if not isinstance(sender, TableFieldHandler):
                    raise ValueError(f"Sender for {attribute} is not TableFieldHandler")
                table_values = words_to_table(words, sender.field_info)
                return panda_value_to_attribute_value(attribute.datatype, table_values)
            case _:
                return panda_value_to_attribute_value(attribute.datatype, value)

    async def update_attribute(
        self, attribute: Attribute, attribute_value: Any
    ) -> None:
        """Dispatch setting logic based on attribute type."""
        match attribute:
            case AttrRW():
                await attribute.set(attribute_value)
                await attribute.update_display_without_process(attribute_value)
            case AttrW():
                await attribute.process(attribute_value)
            case AttrR():
                await attribute.set(attribute_value)

    async def _update(self):
        try:
            changes = await self._raw_panda.get_changes()
            await asyncio.gather(
                *[
                    self.update_field_value(
                        PandaName.from_string(raw_panda_name), value
                    )
                    for raw_panda_name, value in changes.items()
                ]
            )
        # TODO: General exception is not ideal; narrow this dowm.
        except Exception as e:
            LOGGER.error(
                f"Failed to update changes from PandaBlocks client: {e}",
                stack_info=True,
                exc_info=True,
            )
