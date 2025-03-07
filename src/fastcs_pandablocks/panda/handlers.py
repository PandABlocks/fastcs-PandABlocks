from typing import Any

from fastcs.attributes import Attribute, AttrR, AttrW, Handler, Sender, Updater
from fastcs.datatypes import Bool, DataType, Enum, Float, Int, String, T

from fastcs_pandablocks.types import PandaName


def panda_value_to_attribute_value(fastcs_datatype: DataType[T], value: str) -> T:
    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return str(int(value))
        case Int() | Float():
            return fastcs_datatype.dtype(value)
        case Enum():
            return fastcs_datatype.enum_cls[value]

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


def attribute_value_to_panda_value(fastcs_datatype: DataType[T], value: T) -> str:
    match fastcs_datatype:
        case String():
            return value
        case Bool():
            return str(int(value))
        case Int() | Float():
            return str(value)
        case Enum():
            return value.name

        case _:
            raise NotImplementedError(f"Unknown datatype {fastcs_datatype}")


class DefaultFieldSender(Sender):
    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def put(self, controller: Any, attr: AttrW[T], value: T) -> None:
        await controller.put_value_to_panda(self.panda_name, attr.datatype, value)


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


class TableFieldHandler(Handler):
    def __init__(self, panda_name: PandaName):
        self.panda_name = panda_name

    async def update(self, controller: Any, attr: AttrR) -> None:
        # TODO: Convert to panda value
        ...

    async def put(self, controller: Any, attr: AttrW, value: Any) -> None:
        # TODO: Convert to attribtue value
        ...


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
