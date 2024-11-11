from typing import Any

from fastcs.attributes import Attribute, AttrR, AttrW, Handler, Sender, Updater

from fastcs_pandablocks.types import PandaName


class DefaultFieldSender(Sender):
    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def put(self, controller: Any, attr: AttrW, value: str) -> None:
        await controller.put_value_to_panda(self.panda_name, value)


class DefaultFieldUpdater(Updater):
    #: We update the fields from the top level
    update_period = None

    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def update(self, controller: Any, attr: AttrR) -> None:
        pass  # TODO: update the attr with the value from the panda


class DefaultFieldHandler(DefaultFieldSender, DefaultFieldUpdater, Handler):
    def __init__(self, panda_name: PandaName):
        super().__init__(panda_name)


class EguSender(Sender):
    def __init__(self, attr_to_update: Attribute):
        """Update the attr"""
        self.attr_to_update = attr_to_update

    async def put(self, controller: Any, attr: AttrW, value: str) -> None:
        # TODO find out how to update attr_to_update's EGU with the value
        ...


class CaptureHandler(Handler):
    update_period = float("inf")

    def __init__(self, *args, **kwargs):
        pass

    async def update(self, controller: Any, attr: AttrR) -> None: ...
    async def put(self, controller: Any, attr: AttrW, value: Any) -> None: ...


class DatasetHandler(Handler):
    update_period = float("inf")

    def __init__(self, *args, **kwargs): ...  # TODO: work dataset
    async def update(self, controller: Any, attr: AttrR) -> None: ...
    async def put(self, controller: Any, attr: AttrW, value: Any) -> None: ...
