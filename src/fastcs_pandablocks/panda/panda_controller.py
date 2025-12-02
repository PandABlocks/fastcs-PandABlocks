import asyncio
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import Attribute, AttrR
from fastcs.connections import IPConnectionSettings
from fastcs.controllers import Controller
from fastcs.datatypes import Table
from fastcs.logging import bind_logger
from fastcs.methods import Scan
from pandablocks.utils import words_to_table

from fastcs_pandablocks.panda.blocks import Blocks
from fastcs_pandablocks.panda.client_wrapper import RawPanda
from fastcs_pandablocks.panda.io import (
    ArmIO,
    DefaultFieldIO,
    TableFieldIO,
    TableFieldIORef,
    UnitsIO,
    panda_value_to_attribute_value,
)
from fastcs_pandablocks.types import PandaName

logger = bind_logger(__name__)


@dataclass
class PandaControllerSettings:
    poll_period: float
    ip_settings: IPConnectionSettings


class PandaController(Controller):
    """Controller for polling data from the panda through pandablocks-client.

    Changes are received at a given poll period and passed to sub-controllers.
    """

    def __init__(self, settings: PandaControllerSettings) -> None:
        # TODO https://github.com/DiamondLightSource/FastCS/issues/62

        hostname = settings.ip_settings.ip
        self._raw_panda = RawPanda(hostname)
        self._ios = [ArmIO(), DefaultFieldIO(), TableFieldIO(), UnitsIO()]
        self._blocks: Blocks = Blocks(self._raw_panda, ios=self._ios)
        self.update = Scan(self._update, settings.poll_period)
        self.connected = False

        super().__init__(ios=self._ios)

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
            # Numerically named controllers are registered to
            # alphabetically named ControllerVectors, so only
            # alalphabetically named controllers
            # should be registed to top level Controller
            if str(block_name).isalpha():
                self.add_sub_controller(block_name.lower(), block)
                await block.initialise()

    async def update_field_value(self, panda_name: PandaName, value: str | list[str]):
        """Update a panda field with either a single value or a list of words."""

        attribute = self._blocks.get_attribute(panda_name)
        assert isinstance(attribute, AttrR)
        if attribute is None:
            logger.error(f"Couldn't find panda field for {panda_name}.")
            return

        try:
            attribute_value = self._coerce_value_to_panda_type(attribute, value)
        except ValueError:
            logger.opt(exception=True).error("Coerce failed")
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
                io_ref = attribute.io_ref
                if not isinstance(io_ref, TableFieldIORef):
                    raise ValueError(
                        f"AttributeIORef for {attribute} is not TableFieldIORef"
                    )
                table_values = words_to_table(words, io_ref.field_info)
                return panda_value_to_attribute_value(attribute.datatype, table_values)
            case _:
                return panda_value_to_attribute_value(attribute.datatype, value)

    async def update_attribute(self, attribute: AttrR, attribute_value: Any) -> None:
        """Dispatch setting logic based on attribute type."""
        value = attribute.datatype.validate(attribute_value)
        await attribute.update(value)

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
            logger.error(
                f"Failed to update changes from PandaBlocks client: {e}",
                stack_info=True,
                exc_info=True,
            )
