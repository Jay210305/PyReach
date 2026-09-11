"""Parsers for dependency manifests and OSV data."""

from pyreach.parsers.manifest import (
    SOURCE_PIPFILE_LOCK,
    SOURCE_REQUIREMENTS_TXT,
    Dependency,
    ManifestParser,
    ParserResult,
    normalize_name,
)

__all__ = [
    "Dependency",
    "ManifestParser",
    "ParserResult",
    "SOURCE_PIPFILE_LOCK",
    "SOURCE_REQUIREMENTS_TXT",
    "normalize_name",
]