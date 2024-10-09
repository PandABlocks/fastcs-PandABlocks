# TODO: tackle after I have a MVP of the panda part.
from fastcs.controller import Controller
from fastcs.datatypes import Bool, Float, Int, String


class PandaController(Controller):
    def __init__(self, hostname: str) -> None:
        super().__init__()

    async def initialise(self) -> None:
        pass

    async def connect(self) -> None:
        pass
