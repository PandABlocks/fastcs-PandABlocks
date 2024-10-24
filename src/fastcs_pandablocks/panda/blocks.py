from collections.abc import Generator

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import SubController
from pandablocks.responses import BlockInfo

from fastcs_pandablocks.types import EpicsName, PandaName, ResponseType

from .fields import FieldControllerType, get_field_controller_from_field_info


class BlockController(SubController):
    fields: dict[str, FieldControllerType]

    def __init__(
        self,
        panda_name: PandaName,
        number: int | None,
        description: str | None | None,
        raw_fields: dict[str, ResponseType],
    ):
        self._additional_attributes: dict[str, Attribute] = {}
        self.panda_name = panda_name
        self.number = number
        self.description = description
        self.fields = {}

        for field_raw_name, field_info in raw_fields.items():
            field_panda_name = PandaName(field=field_raw_name)
            field = get_field_controller_from_field_info(field_info)
            self.fields[field_panda_name.attribute_name] = field

        super().__init__()

    def initialise(self):
        for field_name, field in self.fields.items():
            if field.additional_attributes:
                self.register_sub_controller(field_name, sub_controller=field)
            if field.top_level_attribute:
                self._additional_attributes[field_name] = field.top_level_attribute

            field.initialise()

    @property
    def additional_attributes(self) -> dict[str, Attribute]:
        return self._additional_attributes


class Blocks:
    _blocks: dict[str, dict[int | None, BlockController]]
    epics_prefix: EpicsName

    def __init__(self):
        self._blocks = {}

    def parse_introspected_data(
        self, blocks: dict[str, BlockInfo], fields: list[dict[str, ResponseType]]
    ):
        self._blocks = {}

        for (block_name, block_info), raw_fields in zip(
            blocks.items(), fields, strict=True
        ):
            iterator = (
                range(1, block_info.number + 1)
                if block_info.number > 1
                else iter(
                    [
                        None,
                    ]
                )
            )
            self._blocks[block_name] = {
                number: BlockController(
                    PandaName(block=block_name, block_number=number),
                    block_info.number,
                    block_info.description,
                    raw_fields,
                )
                for number in iterator
            }

    async def update_field_value(self, panda_name: PandaName, value: str):
        attribute = self[panda_name]

        if isinstance(attribute, AttrW):
            await attribute.process(value)
        elif isinstance(attribute, (AttrRW | AttrR)):
            await attribute.set(value)
        else:
            raise RuntimeError(f"Couldn't find panda field for {panda_name}.")

    def flattened_attribute_tree(
        self,
    ) -> Generator[tuple[str, BlockController], None, None]:
        for blocks in self._blocks.values():
            for block in blocks.values():
                yield (block.panda_name.attribute_name, block)

    def __getitem__(
        self, name: PandaName
    ) -> dict[int | None, BlockController] | BlockController | Attribute:
        if name.block is None:
            raise ValueError(f"Cannot find block for name {name}.")
        blocks = self._blocks[name.block]
        if name.block_number is None:
            return blocks
        block = blocks[name.block_number]
        if name.field is None:
            return block
        field = block.fields[name.field]
        if not name.sub_field:
            assert field.top_level_attribute
            return field.top_level_attribute

        return field.additional_attributes[name.sub_field]
