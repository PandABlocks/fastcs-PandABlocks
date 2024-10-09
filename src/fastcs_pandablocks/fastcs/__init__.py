"""Contains logic relevant to fastcs. Will use `fastcs_pandablocks.panda`."""


from pathlib import Path

from fastcs.backends.epics.backend import EpicsBackend

from .gui import PandaGUIOptions
from .controller import PandaController
from fastcs_pandablocks.types import EpicsName


def ioc(
    panda_hostname: str,
    pv_prefix: EpicsName,
    screens_directory: Path | None,
    clear_bobfiles: bool = False,
):
    controller = PandaController(panda_hostname)
    backend = EpicsBackend(controller, pv_prefix=str(pv_prefix))

    if clear_bobfiles and not screens_directory:
        raise ValueError("`clear_bobfiles` is True with no `screens_directory`")

    if screens_directory:
        if not screens_directory.is_dir():
            raise ValueError(
                f"`screens_directory` {screens_directory} is not a directory"
            )
        backend.create_gui(
            PandaGUIOptions()
        )

    backend.run()
