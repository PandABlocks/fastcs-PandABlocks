import subprocess
import sys

from fastcs_pandablocks import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs_pandablocks", "--version"]
    assert __version__ in subprocess.check_output(cmd).decode().strip()
