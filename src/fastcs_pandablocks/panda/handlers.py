import asyncio
import enum
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrR, AttrRW, AttrW, Handler, Sender, Updater
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T

from fastcs_pandablocks.types import PandaName


def panda_value_to_attribute_value(fastcs_datatype: DataType[T], value: str) -> T:
    """Converts from a value received from the panda through pandablock-client to
    the attribute value.
    """
    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return str(int(value))
        case Int() | Float():
            return fastcs_datatype.dtype(value)
        case Enum():
            return fastcs_datatype.enum_cls[value]

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


def attribute_value_to_panda_value(fastcs_datatype: DataType[T], value: T) -> str:
    """Converts from an attribute value to a value that can be sent to the panda
    with pandablocks-client.
    """
    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return str(int(value))
        case Int() | Float():
            return str(value)
        case Enum():
            return value.name

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


class DefaultFieldSender(Sender):
    """Default sender for sending introspected attributes."""

    def __init__(
        self,
        panda_name: PandaName,
        put_value_to_panda: Callable[
            [PandaName, DataType, Any], Coroutine[None, None, None]
        ],
    ):
        self.panda_name = panda_name
        self.put_value_to_panda = put_value_to_panda

    async def put(self, controller: Any, attr: AttrW[T], value: T) -> None:
        await self.put_value_to_panda(self.panda_name, attr.datatype, value)


class DefaultFieldUpdater(Updater):
    """Default updater for updating introspected attributes."""

    #: We update the fields from the top level
    update_period = None

    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def update(self, controller: Any, attr: AttrR) -> None:
        pass  # TODO: update the attr with the value from the panda


class DefaultFieldHandler(DefaultFieldSender, DefaultFieldUpdater, Handler):
    """Default handler for sending and updating introspected attributes."""

    def __init__(
        self,
        panda_name: PandaName,
        put_value_to_panda: Callable[
            [PandaName, DataType, Any], Coroutine[None, None, None]
        ],
    ):
        super().__init__(panda_name, put_value_to_panda)


class TableFieldHandler(Handler):
    """A handler for updating Table valued attributes."""

    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def update(self, controller: Any, attr: AttrR) -> None:
        # TODO: Convert to panda value
        ...

    async def put(self, controller: Any, attr: AttrW, value: Any) -> None:
        # TODO: Convert to attribtue value
        ...


class CaptureHandler(DefaultFieldHandler):
    """A handler for capture attributes. Not currently used."""


async def _set_attr_if_not_already_value(attribute: AttrRW[T], value: T):
    if attribute.get() != value:
        await attribute.set(value)


@dataclass
class BitGroupOnUpdate:
    """Bits are tied together in bit groups so that when one is set for capture,
    they all are.

    This handler sets all capture attributes in the group when one of them is set.
    """

    capture_attribute: AttrRW[enum.Enum]
    bit_attributes: list[AttrRW[bool]]

    async def __call__(self, value: Any):
        if isinstance(value, enum.Enum):
            bool_value = bool(self.capture_attribute.datatype.index_of(value))  # type: ignore
            enum_value = value
        else:
            bool_value = value
            assert isinstance(self.capture_attribute.datatype, Enum)
            enum_value = self.capture_attribute.datatype.members[int(value)]

        await asyncio.gather(
            *[
                _set_attr_if_not_already_value(bit_attr, bool_value)
                for bit_attr in self.bit_attributes
            ],
            _set_attr_if_not_already_value(self.capture_attribute, enum_value),
        )


class ArmHandler(Handler):
    """A sender for arming and disarming the Pcap."""

    class ArmCommand(enum.Enum):
        DISARM = "Disarm"
        ARM = "Arm"

    def __init__(
        self,
        arm: Callable[[], Coroutine[None, None, None]],
        disarm: Callable[[], Coroutine[None, None, None]],
    ):
        self.arm = arm
        self.disarm = disarm

    async def put(
        self, controller: Any, attr: AttrW[ArmCommand], value: ArmCommand
    ) -> None:
        if value is self.ArmCommand.ARM:
            logging.info("Arming PandA.")
            await self.arm()
        else:
            logging.info("Disarming PandA.")
            await self.disarm()

    async def update(self, controller: Any, attr: AttrR[ArmCommand]) -> None:
        pass
