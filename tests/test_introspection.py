from .mock_asyncio_client import get_mocked_panda_controller
from fastcs.launch import FastCS
from fastcs.transport.epics.pva.adapter import EpicsPVATransport
from fastcs.transport import EpicsPVAOptions, EpicsIOCOptions
from pathlib import Path
import pytest


class TestPanda:
    @pytest.fixture(scope="class")
    def fastcs_cs_instance(self):
        panda_controller, mock_raw_panda = get_mocked_panda_controller(
            Path("introspected_panda.yaml")
        )
        options = EpicsPVAOptions(ioc=EpicsIOCOptions(pv_prefix="INTROSPECTED"))
        FastCS()
        return EpicsPVATransport(panda_controller, options)

    @pytest.mark.asyncio
    async def test_basic_introspection(self, fastcs_cs_instance):
        print("HAHAHA")
        await fastcs_cs_instance.serve()
