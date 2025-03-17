"""Contains logic relevant to fastcs. Will use ``fastcs_pandablocks.panda``."""

from pathlib import Path

from fastcs import FastCS
from fastcs.launch import EpicsPVAOptions
from fastcs.transport import EpicsGUIOptions, EpicsIOCOptions

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
    p4p_ioc_options = EpicsPVAOptions(ioc=EpicsIOCOptions(pv_prefix=pv_prefix))
    if screens_directory:
        if not screens_directory.is_dir():
            raise ValueError(
                f"`screens_directory` {screens_directory} is not a directory"
            )

        gui_options = EpicsGUIOptions(
            output_path=screens_directory / "out.bob", title=pv_prefix
        )
        p4p_ioc_options.gui = gui_options

    controller = PandaController(hostname, poll_period)
    transport = FastCS(controller, [p4p_ioc_options])
    transport.run()


__all__ = ["__version__", "panda", "types", "DEFAULT_POLL_PERIOD"]
