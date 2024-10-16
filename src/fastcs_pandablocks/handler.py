from typing import Any

from fastcs.attributes import AttrW, Sender

from fastcs_pandablocks.types import PandaName


class DefaultFieldSender(Sender):
    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def put(self, controller: Any, attr: AttrW, value: str) -> None:
        await controller.put_value_to_panda(self.panda_name, value)
