"""Source file discovery with configurable ignore patterns.

Provides ``SourceLoader``, a deterministic iterator over Python source files
within a project root. Directories such as virtual environments and caches are
excluded by default, and callers may supply additional glob patterns.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from pyreach.exceptions import ConfigError, ParseError

DEFAULT_EXCLUDES: frozenset[str] = frozenset(
    {
        "venv",
        ".venv",
        ".tox",
        "__pycache__",
        "node_modules",
        ".git",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".eggs",
    }
)


@dataclass(frozen=True)
class SourceFile:
    """A discovered Python source file with its absolute and project-relative paths."""

    path: Path
    rel_path: Path


class SourceLoader:
    """Discover and read Python source files under a project root.

    Default exclusions (always applied, cannot be overridden by user patterns):
        ``venv/``, ``.venv/``, ``.tox/``, ``__pycache__/``, ``node_modules/``,
        ``.git/``, ``build/``, ``dist/``, ``.mypy_cache/``, ``.pytest_cache/``,
        ``.ruff_cache/``, ``.eggs/``.

    User ``ignore_patterns`` are merged on top and support directory prefixes
    (``tests/`` or ``tests``) and glob patterns (``**/migrations/*.py``).
    """

    def __init__(
        self,
        root: Path,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        self._root = root.resolve()
        self._user_patterns = _normalize_patterns(ignore_patterns or [])

    def discover(self) -> list[SourceFile]:
        """Return a deterministically sorted list of Python source files.

        Raises:
            ConfigError: If the project root does not exist.
        """
        if not self._root.is_dir():
            raise ConfigError(f"Project root does not exist: {self._root}")

        result: list[SourceFile] = []

        for py_file in self._root.rglob("*.py"):
            resolved = py_file.resolve()

            if not _is_under(resolved, self._root):
                continue

            rel = resolved.relative_to(self._root)

            if _is_default_excluded(rel):
                continue

            if self._is_user_excluded(rel):
                continue

            result.append(SourceFile(path=resolved, rel_path=rel))

        result.sort(key=lambda sf: sf.rel_path.parts)
        return result

    def read(self, sf: SourceFile) -> str:
        """Read the contents of a source file as UTF-8 text.

        Raises:
            ParseError: If the file cannot be read or decoded.
        """
        try:
            return sf.path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as exc:
            raise ParseError(f"Source file not found: {sf.rel_path}") from exc
        except (UnicodeDecodeError, OSError) as exc:
            raise ParseError(f"Cannot read source file {sf.rel_path}: {exc}") from exc

    def _is_user_excluded(self, rel: Path) -> bool:
        rel_str = str(rel)
        rel_posix = rel.as_posix()
        for pattern in self._user_patterns:
            if pattern.endswith("/"):
                prefix = pattern.rstrip("/")
                parts = rel.parts
                if parts and parts[0] == prefix:
                    return True
                if rel_posix.startswith(prefix + "/"):
                    return True
            elif "*" in pattern or "?" in pattern:
                if fnmatch.fnmatch(rel_posix, pattern):
                    return True
                if fnmatch.fnmatch(rel_str, pattern):
                    return True
            else:
                parts = rel.parts
                if parts and parts[0] == pattern:
                    return True
                if rel_posix.startswith(pattern + "/"):
                    return True
        return False


def _normalize_patterns(patterns: list[str]) -> list[str]:
    """Deduplicate user patterns; strip trailing whitespace."""
    seen: set[str] = set()
    result: list[str] = []
    for p in patterns:
        cleaned = p.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _is_default_excluded(rel: Path) -> bool:
    """Return True if any path component matches a default exclusion."""
    for part in rel.parts:
        if part in DEFAULT_EXCLUDES:
            return True
    return False


def _is_under(child: Path, parent: Path) -> bool:
    """Return True if child is strictly under parent (prevents traversal attacks)."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False
