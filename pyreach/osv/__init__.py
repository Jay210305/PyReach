"""OSV vulnerability ingestion and mapping."""

from importlib import import_module


def __getattr__(name: str) -> object:
    if name in {"ImportStats", "OSVImporter", "sync_osv"}:
        return getattr(import_module("pyreach.osv.importer"), name)
    if name in {"AffectedSymbol", "Vulnerability", "VulnerabilityMapper"}:
        return getattr(import_module("pyreach.osv.mapper"), name)
    raise AttributeError(name)


__all__ = [
    "AffectedSymbol",
    "ImportStats",
    "OSVImporter",
    "Vulnerability",
    "VulnerabilityMapper",
    "sync_osv",
]
