"""Contains logic relevant to fastcs. Will use `fastcs_pandablocks.panda`."""

from pathlib import Path

from fastcs.backends.epics.backend import EpicsBackend
from fastcs.backends.epics.gui import EpicsGUIFormat
from fastcs.backends.epics.ioc import EpicsIOCOptions
from fastcs.backends.epics.util import EpicsNameOptions, PvNamingConvention

from ._version import __version__
from .gui import PandaGUIOptions
from .panda.controller import PandaController

DEFAULT_POLL_PERIOD = 0.1


def ioc(
    epics_prefix: str,
    hostname: str,
    screens_directory: Path | None = None,
    clear_bobfiles: bool = False,
    poll_period: float = DEFAULT_POLL_PERIOD,
    naming_convention: PvNamingConvention = PvNamingConvention.CAPITALIZED,
    pv_separator: str = ":",
):
    name_options = EpicsNameOptions(
        pv_naming_convention=naming_convention, pv_separator=pv_separator
    )
    epics_ioc_options = EpicsIOCOptions(terminal=True, name_options=name_options)

    controller = PandaController(hostname, poll_period)
    backend = EpicsBackend(
        controller, pv_prefix=epics_prefix, ioc_options=epics_ioc_options
    )

    if clear_bobfiles and not screens_directory:
        raise ValueError("`clear_bobfiles` is True with no `screens_directory`")

    if screens_directory:
        if not screens_directory.is_dir():
            raise ValueError(
                f"`screens_directory` {screens_directory} is not a directory"
            )
        if not clear_bobfiles:
            if list(screens_directory.iterdir()):
                raise RuntimeError("`screens_directory` is not empty.")

        backend.create_gui(
            PandaGUIOptions(
                output_path=screens_directory / "output.bob",
                file_format=EpicsGUIFormat.bob,
                title="PandA",
            )
        )

    backend.run()


__all__ = ["__version__", "ioc", "DEFAULT_POLL_PERIOD"]
