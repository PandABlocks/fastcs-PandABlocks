"""Interface for ``python -m fastcs_pandablocks``."""

from fastcs.launch import launch

from fastcs_pandablocks.panda.panda_controller import PandaController

from ._version import __version__

if __name__ == "__main__":
    launch(PandaController, version=__version__)
