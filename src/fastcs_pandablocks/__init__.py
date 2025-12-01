"""Contains logic relevant to fastcs. Will use ``fastcs_pandablocks.panda``."""

from pathlib import Path

from fastcs import FastCS
from fastcs.transports import EpicsGUIOptions, EpicsIOCOptions
from fastcs.transports.epics.pva.transport import EpicsPVATransport

from fastcs_pandablocks.panda.handlers import (
    ArmIO,
    DefaultFieldHandlerIO,
    TableFieldHandlerIO,
    UnitsIO,
)

from . import panda, types
from ._version import __version__
from .panda.panda_controller import PandaController

DEFAULT_POLL_PERIOD = 0.1


def ioc(
    pv_prefix: str,
    hostname: str,
    screens_directory: Path | None = None,
    poll_period: float = DEFAULT_POLL_PERIOD,
):
    p4p_ioc_options = EpicsPVATransport(epicspva=EpicsIOCOptions(pv_prefix=pv_prefix))
    if screens_directory:
        if not screens_directory.is_dir():
            raise ValueError(
                f"`screens_directory` {screens_directory} is not a directory"
            )

        gui_options = EpicsGUIOptions(
            output_path=screens_directory / "out.bob", title=pv_prefix
        )
        p4p_ioc_options.gui = gui_options

    controller = PandaController(
        hostname,
        poll_period,
        ios=[ArmIO(), DefaultFieldHandlerIO(), TableFieldHandlerIO(), UnitsIO()],
    )
    transport = FastCS(controller, [p4p_ioc_options])
    transport.run()


__all__ = ["__version__", "panda", "types", "DEFAULT_POLL_PERIOD"]
