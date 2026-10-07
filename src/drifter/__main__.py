"""Allow running drifter as a module: python -m drifter."""

import sys

from drifter.cli import main

if __name__ == "__main__":
    sys.exit(main())
