"""Interface for ``python -m fastcs_pandablocks``."""

import argparse
import logging

from fastcs_pandablocks.fastcs import ioc

from . import __version__

__all__ = ["main"]


def main():
    """Argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Connect to the given HOST and create an IOC with the given PREFIX."
    )
    parser.add_argument("host", type=str, help="The host to connect to.")
    parser.add_argument("prefix", type=str, help="The prefix for the IOC.")
    parser.add_argument(
        "--screens-dir",
        type=str,
        help=(
            "Provide an existing directory to export generated bobfiles to, if no "
            "directory is provided then bobfiles will not be generated."
        ),
    )
    parser.add_argument(
        "--clear-bobfiles",
        action="store_true",
        help="Clear bobfiles from the given `screens-dir` before generating new ones.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Set the logging level.",
    )

    parsed_args = parser.parse_args()

    # Set the logging level
    level = getattr(logging, parsed_args.log_level.upper(), None)
    logging.basicConfig(format="%(levelname)s:%(message)s", level=level)

    ioc(
        parsed_args.host,
        parsed_args.prefix,
        parsed_args.screens_dir,
        parsed_args.clear_bobfiles,
    )


if __name__ == "__main__":
    main()
