from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pyreach.exceptions import ParseError
from pyreach.parsers.manifest import (
    SOURCE_REQUIREMENTS_TXT,
    Dependency,
    ManifestParser,
    normalize_name,
)


def test_dependency_is_frozen() -> None:
    dep = Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)
    with pytest.raises(FrozenInstanceError):
        dep.name = "urllib3"


def test_dependency_normalizes_name() -> None:
    assert normalize_name("Foo_Bar.Baz") == "foo-bar-baz"


def test_dependency_rejects_empty_name() -> None:
    with pytest.raises(ParseError):
        Dependency(name="", version="1.0.0", source=SOURCE_REQUIREMENTS_TXT)


def test_dependency_rejects_unknown_source() -> None:
    with pytest.raises(ParseError):
        Dependency(name="requests", version="2.31.0", source="pyproject.toml")


def test_manifest_parser_is_protocol() -> None:
    class DummyParser:
        source_name = SOURCE_REQUIREMENTS_TXT

        def supports(self, path: Path) -> bool:
            return True

        def parse(self, path: Path) -> list[Dependency]:
            return []

    assert isinstance(DummyParser(), ManifestParser)