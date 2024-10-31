"""Interface for ``python -m fastcs_pandablocks``."""

import argparse
import logging
from pathlib import Path

from fastcs.backends.epics.util import PvNamingConvention

from fastcs_pandablocks import DEFAULT_POLL_PERIOD, ioc

from . import __version__

__all__ = ["main"]


def main():
    """Argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Connect to the given HOST and create an IOC with the given PREFIX."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser(
        "run", help="Run the IOC with the given HOST and PREFIX."
    )
    run_parser.add_argument("hostname", type=str, help="The host to connect to.")
    run_parser.add_argument("prefix", type=str, help="The prefix for the IOC.")
    run_parser.add_argument(
        "--screens-dir",
        type=str,
        help=(
            "Provide an existing directory to export generated bobfiles to, if no "
            "directory is provided then bobfiles will not be generated."
        ),
    )
    run_parser.add_argument(
        "--clear-bobfiles",
        action="store_true",
        help=(
            "Overwrite existing bobfiles from the given `screens-dir` "
            "before generating new ones."
        ),
    )

    run_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Set the logging level.",
    )
    run_parser.add_argument(
        "--poll-period",
        default=DEFAULT_POLL_PERIOD,
        type=float,
        help="Period in seconds with which to poll the panda.",
    )
    run_parser.add_argument(
        "--pv-naming-convention",
        default=PvNamingConvention.CAPITALIZED.name,
        choices=[choice.name for choice in PvNamingConvention],
        help="Naming convention of the EPICS PVs.",
    )
    run_parser.add_argument(
        "--pv-separator",
        default=":",
        type=str,
        help="Separator to use between EPICS PV sections.",
    )

    parsed_args = parser.parse_args()
    if parsed_args.command != "run":
        return

    # Set the logging level
    level = getattr(logging, parsed_args.log_level.upper(), None)
    logging.basicConfig(format="%(levelname)s:%(message)s", level=level)

    ioc(
        parsed_args.prefix,
        parsed_args.hostname,
        screens_directory=Path(parsed_args.screens_dir),
        clear_bobfiles=parsed_args.clear_bobfiles,
        poll_period=parsed_args.poll_period,
        naming_convention=PvNamingConvention(parsed_args.pv_naming_convention),
        pv_separator=parsed_args.pv_separator,
    )


if __name__ == "__main__":
    main()
