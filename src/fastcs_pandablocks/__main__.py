"""Interface for ``python -m fastcs_pandablocks``."""

from fastcs import launch

from fastcs_pandablocks import __version__
from fastcs_pandablocks.panda.panda_controller import PandaController

launch(controller_classes=PandaController, version=__version__)
