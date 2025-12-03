import enum
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import (
    AttributeIO,
    AttributeIORef,
    AttrW,
)
from fastcs.datatypes import DType_T


class ArmCommand(enum.Enum):
    """Enum class for PandA arm fields."""

    DISARM = "Disarm"
    ARM = "Arm"


@dataclass
class ArmIORef(AttributeIORef):
    arm: Callable[[], Coroutine[None, None, None]]
    disarm: Callable[[], Coroutine[None, None, None]]


class ArmIO(AttributeIO[DType_T, ArmIORef]):
    """A sender for arming and disarming the Pcap."""

    async def send(self, attr: AttrW[DType_T, ArmIORef], value: Any):
        if value is ArmCommand.ARM:
            logging.info("Arming PandA.")
            await attr.io_ref.arm()
        else:
            logging.info("Disarming PandA.")
            await attr.io_ref.disarm()
