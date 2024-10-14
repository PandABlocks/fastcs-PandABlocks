"""Contains logic relevant to fastcs. Will use `fastcs_pandablocks.panda`."""

from pathlib import Path

from fastcs.backends.epics.backend import EpicsBackend
from fastcs.backends.epics.gui import EpicsGUIFormat

from ._version import __version__
from .controller import PandaController
from .gui import PandaGUIOptions
from .types import EpicsName

__all__ = ["__version__"]


def ioc(
    prefix: EpicsName,
    hostname: str,
    screens_directory: Path | None,
    clear_bobfiles: bool = False,
):
    controller = PandaController(prefix, hostname)
    backend = EpicsBackend(controller, pv_prefix=str(prefix))

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
