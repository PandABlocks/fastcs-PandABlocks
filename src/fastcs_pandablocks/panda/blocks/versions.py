import logging
import re
from typing import TypedDict

from fastcs.attributes import AttrR
from fastcs.controller import SubController
from fastcs.datatypes import String

from fastcs_pandablocks.types import WidgetGroup


class PandaVersions(TypedDict):
    panda_sw: str
    fpga: str
    rootfs: str


def _parse_idn_response(idn_response: str) -> PandaVersions:
    """Function that parses version info from the PandA's response to the IDN command

    See: https://pandablocks-server.readthedocs.io/en/latest/commands.html#system-commands
    """

    # Currently, IDN reports sw, fpga, and rootfs versions
    firmware_versions = {"PandA SW": "Unknown", "FPGA": "Unknown", "rootfs": "Unknown"}

    # If the *IDN response contains too many keys, break and leave versions as "Unknown"
    # Since spaces are used to deliminate versions and can also be in the keys and
    # values, if an additional key is present that we don't explicitly handle,
    # our approach of using regex matching will not work.
    if sum(name in idn_response for name in firmware_versions) < idn_response.count(
        ":"
    ):
        logging.error(
            f"Recieved unexpected version numbers in version string {idn_response}!"
        )
    else:
        for firmware_name in firmware_versions:
            pattern = re.compile(
                rf"{re.escape(firmware_name)}:\s*([^:]+?)(?=\s*\b(?: \
                {'|'.join(map(re.escape, firmware_versions))}):|$)"
            )
            if match := pattern.search(idn_response):
                firmware_versions[firmware_name] = match.group(1).strip()
                logging.info(
                    f"{firmware_name} Version: {firmware_versions[firmware_name]}"
                )
            else:
                logging.warning(f"Failed to get {firmware_name} version information!")

    return PandaVersions(
        panda_sw=firmware_versions["PandA SW"],
        fpga=firmware_versions["FPGA"],
        rootfs=firmware_versions["rootfs"],
    )


class VersionController(SubController):
    def __init__(self, idn_response: str):
        super().__init__()
        self.description = "Version information from the PandA."
        versions = _parse_idn_response(idn_response)
        for version_name, version in versions.items():
            self.attributes[version_name] = AttrR(
                String(),
                description="Version information from the PandA.",
                group=WidgetGroup.READBACKS.value,
                initial_value=version,  # type: ignore
            )
