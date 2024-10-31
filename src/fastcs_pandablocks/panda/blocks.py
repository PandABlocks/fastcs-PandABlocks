from collections.abc import Generator

from fastcs.attributes import Attribute, AttrR, AttrRW, AttrW
from fastcs.controller import SubController

from fastcs_pandablocks.types import (
    EpicsName,
    PandaName,
    RawBlocksType,
    RawFieldsType,
    RawInitialValuesType,
)
from fastcs_pandablocks.types.annotations import ResponseType

from .fields import (
    FieldControllerType,
    get_field_controller_from_field_info,
)


def _def_pop_up_to_block_or_field(name: PandaName, dictionary: RawInitialValuesType):
    extracted_members = {}
    resolution_method = (
        PandaName.up_to_block if name.field is None else PandaName.up_to_field
    )

    # So the dictionary can be changed during iteration.
    for sub_name in list(dictionary):
        if resolution_method(sub_name) == name:
            extracted_members[sub_name] = dictionary.pop(sub_name)
    return extracted_members


class BlockController(SubController):
    fields: dict[PandaName, FieldControllerType]

    def __init__(
        self,
        panda_name: PandaName,
        description: str | None | None,
        field_infos: dict[PandaName, ResponseType],
        initial_values: RawInitialValuesType,
        label: str | None,
    ):
        self.panda_name = panda_name
        self.description = description
        self.label = label

        self._additional_attributes: dict[str, Attribute] = {}
        self.fields: dict[PandaName, FieldControllerType] = {}

        for field_name, field_info in field_infos.items():
            field_name = panda_name + field_name
            field_initial_values = _def_pop_up_to_block_or_field(
                field_name, initial_values
            )
            self.fields[field_name] = get_field_controller_from_field_info(
                field_name, field_info, field_initial_values, label
            )

        super().__init__()

    def initialise(self):
        for field_name, field in self.fields.items():
            if field.additional_attributes:
                self.register_sub_controller(
                    field_name.attribute_name, sub_controller=field
                )
            field.initialise()  # Registers `field.sub_contollers`.
            if field.top_level_attribute:
                assert field_name.field is not None
                self._additional_attributes[field_name.field] = (
                    field.top_level_attribute
                )

    @property
    def additional_attributes(self) -> dict[str, Attribute]:
        return self._additional_attributes


class Blocks:
    _blocks: dict[PandaName, BlockController]
    epics_prefix: EpicsName

    def __init__(self):
        self._blocks = {}

    def parse_introspected_data(
        self,
        blocks: RawBlocksType,
        field_infos: RawFieldsType,
        labels: RawInitialValuesType,
        initial_values: RawInitialValuesType,
    ):
        self._blocks = {}

        for (block_name, block_info), field_info in zip(
            blocks.items(), field_infos, strict=True
        ):
            numbered_block_names = (
                [block_name]
                if block_info.number in (None, 1)
                else [
                    block_name + PandaName(block_number=number)
                    for number in range(1, block_info.number + 1)
                ]
            )

            for numbered_block_name in numbered_block_names:
                block_initial_values = _def_pop_up_to_block_or_field(
                    numbered_block_name, initial_values
                )
                label = labels.get(numbered_block_name, None)

                self._blocks[numbered_block_name] = BlockController(
                    numbered_block_name,
                    block_info.description,
                    field_info,
                    block_initial_values,
                    label,
                )

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
        for block in self._blocks.values():
            yield (block.panda_name.attribute_name, block)

    def __getitem__(self, name: PandaName) -> BlockController | Attribute | None:
        block = self._blocks[name.up_to_block()]
        if name.field is None:
            return block
        field = block.fields[name.up_to_field()]
        if name.sub_field is None:
            return field.top_level_attribute
        return field.additional_attributes[name.sub_field]
