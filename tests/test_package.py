"""Smoke tests for the LifeLenz package foundation."""

from importlib import import_module

import lifelenz


def test_package_can_be_imported() -> None:
    """The installed package is importable by its public name."""
    assert import_module("lifelenz") is lifelenz


def test_package_version() -> None:
    """The package exposes the initial project version."""
    assert lifelenz.__version__ == "0.1.0"


def test_package_public_exports() -> None:
    """The public package surface deliberately exports the version."""
    assert lifelenz.__all__ == ["__version__"]
