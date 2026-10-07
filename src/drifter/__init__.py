"""Drifter — Universal AI Agent Drift Guard."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("drifter-check")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
