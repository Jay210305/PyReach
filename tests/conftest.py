"""PyReach shared pytest fixtures and test factories.

This module provides common fixtures for tests across all implementation sprints:
- Filesystem & directory scaffolds (`project_root`, `sample_requirements_txt`)
- Factory functions for dynamic test inputs (`make_requirements`)
- In-memory / temporary SQLite database harnesses (`sqlite_db`)
- Standardized OSV vulnerability records and JSONL dumps (`sample_osv_record`, `sample_osv_jsonl`)
- Test isolation hooks (`reset_logging`)

All temporary files and databases use pytest's `tmp_path` fixture to prevent
inter-test pollution and state leakage.
"""

import json
import logging
import sqlite3
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any

import pytest

from pyreach.db.connection import initialize_database


@pytest.fixture(autouse=True)
def reset_logging() -> Generator[None, None, None]:
    """Ensure logging handlers and level are isolated between test runs."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    yield
    root_logger.handlers = original_handlers
    root_logger.setLevel(original_level)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Return a temporary directory configured as an empty project root."""
    return tmp_path


@pytest.fixture
def make_requirements(tmp_path: Path) -> Callable[[list[str]], Path]:
    """Factory fixture to create custom requirements.txt files with arbitrary lines."""

    def _factory(lines: list[str], filename: str = "requirements.txt") -> Path:
        req_file = tmp_path / filename
        req_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return req_file

    return _factory


@pytest.fixture
def sample_requirements_txt(tmp_path: Path) -> Path:
    """Return a valid requirements.txt containing pinned, ranged, and extra dependencies."""
    req_file = tmp_path / "requirements.txt"
    content = "requests==2.31.0\nflask>=2.2.0,<3.0.0\nurllib3~=1.26.15\nclick[extra]==8.1.3\n"
    req_file.write_text(content, encoding="utf-8")
    return req_file


@pytest.fixture
def sample_pipfile_lock(tmp_path: Path) -> Path:
    """Return a valid Pipfile.lock containing standard 'default' and 'develop' sections."""
    lock_file = tmp_path / "Pipfile.lock"
    data = {
        "_meta": {
            "hash": {"sha256": "abcdef1234567890"},
            "pipfile-spec": 6,
            "requires": {"python_version": "3.10"},
            "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}],
        },
        "default": {
            "requests": {
                "hashes": ["sha256:1111"],
                "index": "pypi",
                "version": "==2.31.0",
            },
            "flask": {
                "hashes": ["sha256:2222"],
                "index": "pypi",
                "version": "==2.2.5",
            },
        },
        "develop": {
            "pytest": {
                "hashes": ["sha256:3333"],
                "index": "pypi",
                "version": "==7.4.0",
            },
        },
    }
    lock_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return lock_file


@pytest.fixture
def sample_osv_record() -> dict[str, Any]:
    """Return a dictionary representing a valid OSV record for a PyPI package."""
    return {
        "id": "GHSA-1111-2222-3333",
        "summary": "Sample PyPI advisory for requests",
        "aliases": ["CVE-2023-32681"],
        "modified": "2023-06-01T12:00:00Z",
        "published": "2023-05-22T10:00:00Z",
        "severity": [{"type": "CVSS_V3", "score": "7.5"}],
        "database_specific": {"severity": "HIGH"},
        "affected": [
            {
                "package": {"name": "requests", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "2.0.0"}, {"fixed": "2.31.0"}],
                    }
                ],
                "ecosystem_specific": {
                    "imports": [
                        {"symbols": ["requests.sessions.Session.request", "requests.api.get"]}
                    ]
                },
            }
        ],
    }


@pytest.fixture
def sample_osv_jsonl(tmp_path: Path, sample_osv_record: dict[str, Any]) -> Path:
    """Return a path to a JSONL file with 5 records covering PyPI, npm, and malformed lines."""
    records = [
        sample_osv_record,
        {
            "id": "GHSA-4444-5555-6666",
            "summary": "Vulnerability in flask without explicit symbols",
            "aliases": ["CVE-2023-30861"],
            "modified": "2023-05-10T12:00:00Z",
            "published": "2023-05-02T10:00:00Z",
            "severity": [{"type": "CVSS_V3", "score": "9.8"}],
            "affected": [
                {
                    "package": {"name": "flask", "ecosystem": "PyPI"},
                    "ranges": [
                        {
                            "type": "ECOSYSTEM",
                            "events": [{"introduced": "2.0.0"}, {"fixed": "2.2.5"}],
                        }
                    ],
                }
            ],
        },
        {
            "id": "GHSA-NPM-7777-8888",
            "summary": "Vulnerability in npm lodash package",
            "aliases": ["CVE-2021-23337"],
            "modified": "2023-01-01T00:00:00Z",
            "published": "2021-02-15T00:00:00Z",
            "affected": [
                {
                    "package": {"name": "lodash", "ecosystem": "npm"},
                    "ranges": [
                        {
                            "type": "ECOSYSTEM",
                            "events": [{"introduced": "0"}, {"fixed": "4.17.21"}],
                        }
                    ],
                }
            ],
        },
        "{not valid json line}",
        {
            "id": "GHSA-9999-0000-1111",
            "summary": "Low severity package vulnerability",
            "modified": "2022-01-01T00:00:00Z",
            "published": "2022-01-01T00:00:00Z",
            "severity": [{"type": "CVSS_V3", "score": "3.5"}],
            "affected": [
                {
                    "package": {"name": "urllib3", "ecosystem": "PyPI"},
                    "ranges": [
                        {
                            "type": "ECOSYSTEM",
                            "events": [{"introduced": "1.26.0"}, {"fixed": "1.26.5"}],
                        }
                    ],
                }
            ],
        },
    ]

    p = tmp_path / "osv_sample.jsonl"
    lines: list[str] = []
    for item in records:
        if isinstance(item, str):
            lines.append(item)
        else:
            lines.append(json.dumps(item))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


@pytest.fixture
def sqlite_db(
    tmp_path: Path,
) -> Generator[tuple[Path, Callable[[], sqlite3.Connection]], None, None]:
    """Provide an initialized SQLite database path and a connection context factory."""
    db_path = tmp_path / "test_pyreach.db"
    initialize_database(db_path)

    def _conn_factory() -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    yield db_path, _conn_factory
