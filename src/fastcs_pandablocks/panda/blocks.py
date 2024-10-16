from collections.abc import Generator

from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.controller import SubController
from pandablocks.responses import BlockInfo

from fastcs_pandablocks.types import AttrType, EpicsName, PandaName, ResponseType

from .fields import FIELD_TYPE_TO_FASTCS_TYPE, FieldType


class BlockController(SubController):
    fields: dict[str, FieldType]

    def __init__(
        self,
        panda_name: PandaName,
        number: int | None,
        description: str | None | None,
        raw_fields: dict[str, ResponseType],
    ):
        super().__init__()
        self.panda_name = panda_name
        self.number = number
        self.description = description
        self.fields = {}

        for field_raw_name, field_info in raw_fields.items():
            field_panda_name = self.panda_name + PandaName(field=field_raw_name)

            field = FIELD_TYPE_TO_FASTCS_TYPE[field_info.type][field_info.subtype](
                # TODO make type safe after match statment
                field_panda_name,
                field_info,  # type: ignore
            )
            self.fields[field_raw_name] = field
            if field.block_attribute:
                setattr(self, *field.block_attribute)
            if field.sub_field_controller:
                self.register_sub_controller(
                    field_panda_name.attribute_name, field.sub_field_controller
                )


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
        self, name: EpicsName | PandaName
    ) -> dict[int | None, BlockController] | BlockController | AttrType:
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
            assert field.block_attribute
            return field.block_attribute.attribute

        sub_field = getattr(field.sub_field_controller, name.sub_field)
        return sub_field
