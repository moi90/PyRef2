"""PyRef2 package entrypoint and public exports."""

from pyref2.cli.commands import main as cli_main

__all__ = ["main", "__version__"]
__version__ = "0.1.0"


def main() -> int:
    """Run the command line interface."""
    return cli_main()
