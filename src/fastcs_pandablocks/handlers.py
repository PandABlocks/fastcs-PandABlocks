from typing import Any

from fastcs.attributes import AttrW, Handler, Sender

from fastcs_pandablocks.types import AttrType, PandaName


class DefaultFieldSender(Sender):
    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def put(self, controller: Any, attr: AttrW, value: str) -> None:
        await controller.put_value_to_panda(self.panda_name, value)


class UpdateEguSender(Sender):
    def __init__(self, attr_to_update: AttrType):
        """Update the attr"""
        self.attr_to_update = attr_to_update

    async def put(self, controller: Any, attr: AttrW, value: str) -> None:
        # TODO find out how to update attr_to_update's EGU with the value
        ...
