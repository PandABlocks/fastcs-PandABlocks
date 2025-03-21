from collections import defaultdict
from typing import Generator
import asyncio
from dataclasses import dataclass
from collections.abc import AsyncGenerator, Iterator
from io import BufferedReader
from pathlib import Path
from unittest import mock

import yaml
from fastcs.datatypes import DataType, T
from pandablocks.connections import DataConnection
from pandablocks.responses import (
    BlockInfo,
    BitMuxFieldInfo,
    BitOutFieldInfo,
    Data,
    EnumFieldInfo,
    ExtOutBitsFieldInfo,
    ExtOutFieldInfo,
    FieldInfo,
    PosMuxFieldInfo,
    PosOutFieldInfo,
    ScalarFieldInfo,
    SubtypeTimeFieldInfo,
    TableFieldDetails,
    TableFieldInfo,
    TimeFieldInfo,
    UintFieldInfo,
)

from fastcs_pandablocks.panda.panda_controller import PandaController
from fastcs_pandablocks.types import RawBlocksType, RawFieldsType, RawInitialValuesType
from fastcs_pandablocks.types._string_types import PandaName


def chunked_read(f: BufferedReader, size: int) -> Iterator[bytes]:
    data = f.read(size)
    while data:
        yield data
        data = f.read(size)


def get_unpack_constructor(type):
    def basic_constructor(loader, node):
        mapping = loader.construct_mapping(node, deep=True)
        return type(**mapping)

    return basic_constructor


def yaml_load(yaml_path: Path):
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:__main__.MockPandaData",
        get_unpack_constructor(MockPandaData),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:fastcs_pandablocks.types._string_types.PandaName",
        get_unpack_constructor(PandaName),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.BlockInfo",
        get_unpack_constructor(BlockInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.FieldInfo",
        get_unpack_constructor(FieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.BitOutFieldInfo",
        get_unpack_constructor(BitOutFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.PosMuxFieldInfo",
        get_unpack_constructor(PosMuxFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.EnumFieldInfo",
        get_unpack_constructor(EnumFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.UintFieldInfo",
        get_unpack_constructor(UintFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.PosOutFieldInfo",
        get_unpack_constructor(PosOutFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.BitMuxFieldInfo",
        get_unpack_constructor(BitMuxFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.SubtypeTimeFieldInfo",
        get_unpack_constructor(SubtypeTimeFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.ExtOutFieldInfo",
        get_unpack_constructor(ExtOutFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.ExtOutBitsFieldInfo",
        get_unpack_constructor(ExtOutBitsFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.TableFieldInfo",
        get_unpack_constructor(TableFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.TableFieldDetails",
        get_unpack_constructor(TableFieldDetails),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.TimeFieldInfo",
        get_unpack_constructor(TimeFieldInfo),
    )
    yaml.add_constructor(
        "tag:yaml.org,2002:python/object:pandablocks.responses.ScalarFieldInfo",
        get_unpack_constructor(ScalarFieldInfo),
    )

    with yaml_path.open() as f:
        return yaml.load(f, Loader=yaml.FullLoader)


@dataclass
class MockPandaData:
    """
    Args:
        get_responses (dict):
            Key-value pairs of what the ``Get`` response of a command should be.
        get_changes_defaults (Any):
            The default value of get_changes if nothing is added to the queue.
        blocks (Any):
            The introspected blocks.
        fields (Any):
            The introspected fields.
        initial_values (Any):
            The introspected ``*CHANGES``.
        labels (Any):
            The introspected labels.
    """

    get_responses: dict[str, str]
    get_changes_defaults: dict[str, str]
    blocks: RawBlocksType
    fields: RawFieldsType
    labels: RawInitialValuesType
    initial_values: RawInitialValuesType


class _MockedRawPanda:
    _mock_yaml_path: Path

    def __init__(
        self,
        hostname: str,
    ) -> None:
        self._mock_panda_data = yaml_load(self._mock_yaml_path)

        self.connected = False
        self.armed = False

        self.get_changes_queue = asyncio.Queue()
        self.get_queue = asyncio.Queue()
        self.sent: dict[str, list[str]] = defaultdict(list)

    async def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    async def put_value_to_panda(
        self, panda_name: PandaName, fastcs_datatype: DataType[T], value: T
    ):
        pass

    async def introspect(self):
        return (
            self._mock_panda_data.blocks,
            self._mock_panda_data.fields,
            self._mock_panda_data.labels,
            self._mock_panda_data.initial_values,
        )

    async def send(self, name: str, value: str):
        self.sent[name].append(value)

    async def get(self, name: str) -> str | list[str]:
        try:
            return self.get_queue.get_nowait()
        except asyncio.QueueEmpty:
            return self._mock_panda_data.get_responses[name]

    async def get_changes(self) -> dict[str, str]:
        try:
            return self.get_changes_queue.get_nowait()
        except asyncio.QueueEmpty:
            return self._mock_panda_data.get_changes_defaults

    async def arm(self):
        self.armed = True

    async def disarm(self):
        self.armed = False

    async def data(
        self, scaled: bool, flush_period: float
    ) -> AsyncGenerator[Data, None]:
        flush_every_frame = flush_period is None
        conn = DataConnection()
        conn.connect(scaled)
        with open(Path(__file__).parent / "raw_dump.dat", "rb") as f:
            for raw in chunked_read(f, 200000):
                for data in conn.receive_bytes(
                    raw, flush_every_frame=flush_every_frame
                ):
                    yield data


def get_mocked_panda_controller(
    yaml_path: Path,
    poll_period: float = 0.1,
) -> tuple[PandaController, _MockedRawPanda]:
    full_yaml_path = (
        yaml_path
        if yaml_path.exists()
        else Path(__file__).parent / "mock_data" / yaml_path
    )

    class MockedRawPanda(_MockedRawPanda):
        _mock_yaml_path = full_yaml_path

    with mock.patch(
        "fastcs_pandablocks.panda.panda_controller.RawPanda", MockedRawPanda
    ):
        controller = PandaController("no hostname for mock", poll_period)
        return controller, controller._raw_panda  # type: ignore
