"""Manifest parsing data contract and parser protocol.

:class:`Dependency` is the stable data contract consumed by every manifest
parser (requirements.txt, Pipfile.lock) and by the OSV mapper. The
:class:`ManifestParser` protocol is the interface every manifest parser must
implement so the CLI can auto-select a parser by filename without hard-coded
logic.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from pyreach.exceptions import ParseError

SOURCE_REQUIREMENTS_TXT = "requirements.txt"
SOURCE_PIPFILE_LOCK = "Pipfile.lock"
VALID_SOURCES = frozenset({SOURCE_REQUIREMENTS_TXT, SOURCE_PIPFILE_LOCK})


def normalize_name(name: str) -> str:
    """Return the PEP 503 normalized form of *name*.

    Lowercases the name and collapses runs of ``-``, ``_`` and ``.`` into a
    single ``-`` (``Foo_Bar.Baz`` -> ``foo-bar-baz``).
    """
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Dependency:
    """A single resolved dependency parsed from a manifest.

    ``name`` MUST be PEP 503 normalized (see :func:`normalize_name`). For exact
    pins ``version`` keeps the literal (``"2.31.0"``); for version ranges it
    stores the resolved lower bound with the comparison operator stripped
    (``">=2.0.0"`` -> ``"2.0.0"``). ``source`` is one of
    :data:`SOURCE_REQUIREMENTS_TXT` or :data:`SOURCE_PIPFILE_LOCK`.
    """

    name: str
    version: str
    source: str
    extra: str | None = None
    marker: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ParseError(f"dependency name must be non-empty, got {self.name!r}")
        if self.source not in VALID_SOURCES:
            raise ParseError(
                f"unknown dependency source {self.source!r}; "
                f"expected one of {sorted(VALID_SOURCES)}"
            )


#: Parsers return a plain list of dependencies. The alias keeps future typing
#: migrations cheap without changing the runtime contract.
ParserResult = list[Dependency]


@runtime_checkable
class ManifestParser(Protocol):
    """Interface every manifest parser must implement.

    ``supports()`` lets the CLI auto-select a parser by filename.
    ``parse()`` raises :class:`~pyreach.exceptions.ConfigError` when the file
    is missing and :class:`~pyreach.exceptions.ParseError` when it is malformed.
    ``parse()`` never executes the file (no ``eval``, no ``pip``); it only
    reads and parses text.
    """

    source_name: str = ""

    def supports(self, path: Path) -> bool: ...

    def parse(self, path: Path) -> list[Dependency]: ...