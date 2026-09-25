"""Parsers for dependency manifests and OSV data."""

from pyreach.parsers.manifest import (
    SOURCE_PIPFILE_LOCK,
    SOURCE_REQUIREMENTS_TXT,
    Dependency,
    ManifestParser,
    ParserResult,
    PipfileLockParser,
    RequirementsTxtParser,
    normalize_name,
    select_manifest_parser,
)

__all__ = [
    "Dependency",
    "ManifestParser",
    "ParserResult",
    "PipfileLockParser",
    "RequirementsTxtParser",
    "SOURCE_PIPFILE_LOCK",
    "SOURCE_REQUIREMENTS_TXT",
    "normalize_name",
    "select_manifest_parser",
]
