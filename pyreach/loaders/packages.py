"""Installed package resolver mapping dependency names to site-packages paths."""

from __future__ import annotations

import importlib.metadata
import json
import logging
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from pyreach.parsers.manifest import normalize_name

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyreach.parsers.manifest import Dependency

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstalledPackage:
    """An installed Python package discovered in a virtual environment or site-packages."""

    name: str  # normalized distribution name (PEP 503)
    version: str
    location: Path  # directory containing the importable package or editable source
    top_level: list[str]  # list of top-level importable module or package names


def _infer_top_level(files: Iterable[PurePath]) -> list[str]:
    """Infer top-level module names from a distribution's file listing."""
    inferred: set[str] = set()
    for file_path in files:
        parts = file_path.parts
        if not parts or parts[0].endswith((".dist-info", ".egg-info")):
            continue
        if len(parts) >= 2 and parts[1] == "__init__.py":
            inferred.add(parts[0])
        elif len(parts) == 1 and parts[0].endswith(".py"):
            inferred.add(parts[0][:-3])
    return sorted(inferred)


def _sys_path_site_packages() -> list[Path]:
    """Return the current environment's site-packages directories from ``sys.path``."""
    seen: set[Path] = set()
    result: list[Path] = []
    for entry in sys.path:
        candidate = Path(entry)
        if candidate.name == "site-packages" and candidate.is_dir():
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(resolved)
    return result


class PackageResolver:
    """Resolve installed Python packages from a virtualenv or site-packages."""

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        self.search_paths = (
            [p.resolve() for p in search_paths] if search_paths is not None else None
        )
        self._cache: dict[str, InstalledPackage] | None = None

    def _get_distributions(self) -> Iterable[importlib.metadata.Distribution]:
        """Enumerate distributions from search_paths or sys.path."""
        if self.search_paths is not None:
            return importlib.metadata.distributions(path=[str(p) for p in self.search_paths])
        return importlib.metadata.distributions()

    def _site_packages_dirs(self) -> list[Path]:
        if self.search_paths is not None:
            return self.search_paths
        return _sys_path_site_packages()

    def _load_egg_links(self) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for sp in self._site_packages_dirs():
            if not sp.is_dir():
                continue
            for egg_link in sp.glob("*.egg-link"):
                try:
                    content = egg_link.read_text(encoding="utf-8").strip()
                except OSError:
                    continue
                if not content:
                    continue
                first_line = content.splitlines()[0].strip()
                if first_line:
                    result[egg_link.stem] = Path(first_line).resolve()
        return result

    def _load_cache(self) -> dict[str, InstalledPackage]:
        if self._cache is not None:
            return self._cache

        egg_links = self._load_egg_links()

        cache: dict[str, InstalledPackage] = {}
        for dist in self._get_distributions():
            raw_name: str | None = None
            if dist.metadata and "Name" in dist.metadata:
                raw_name = dist.metadata["Name"]
            if not raw_name:
                continue

            norm_name = normalize_name(raw_name)
            version = dist.version or ""

            location = Path(str(dist.locate_file(""))).resolve()
            direct_url_text = dist.read_text("direct_url.json")
            if direct_url_text:
                try:
                    direct_url_data = json.loads(direct_url_text)
                    if isinstance(direct_url_data, dict) and "url" in direct_url_data:
                        parsed_url = urllib.parse.urlparse(direct_url_data["url"])
                        if parsed_url.scheme == "file":
                            local_path = urllib.request.url2pathname(parsed_url.path)
                            location = Path(local_path).resolve()
                except (json.JSONDecodeError, ValueError, OSError):
                    pass

            if raw_name in egg_links:
                location = egg_links[raw_name]

            top_level: list[str] = []
            top_level_text = dist.read_text("top_level.txt")
            if top_level_text:
                top_level = [line.strip() for line in top_level_text.splitlines() if line.strip()]

            if not top_level:
                record_text = dist.read_text("RECORD")
                if record_text:
                    record_paths = [
                        Path(line.split(",")[0].strip())
                        for line in record_text.splitlines()
                        if line.strip()
                    ]
                    top_level = _infer_top_level(record_paths)

            if not top_level and dist.files:
                top_level = _infer_top_level(dist.files)

            if not top_level:
                top_level = [raw_name.replace("-", "_")]

            cache[norm_name] = InstalledPackage(
                name=norm_name,
                version=version,
                location=location,
                top_level=top_level,
            )

        self._cache = cache
        return self._cache

    def resolve(self, name: str) -> InstalledPackage | None:
        """Resolve a distribution name to an InstalledPackage, or None if not found."""
        cache = self._load_cache()
        return cache.get(normalize_name(name))

    def resolve_all(self, deps: list[Dependency]) -> dict[str, InstalledPackage]:
        """Resolve a list of dependencies to their InstalledPackage records."""
        result: dict[str, InstalledPackage] = {}
        for dep in deps:
            pkg = self.resolve(dep.name)
            if pkg is not None:
                result[pkg.name] = pkg
        return result


def _venv_site_packages(venv: Path) -> list[Path]:
    site_dirs: list[Path] = []
    for sub in ("Lib", "lib"):
        site = venv / sub / "site-packages"
        if site.is_dir():
            site_dirs.append(site.resolve())

    lib_dir = venv / "lib"
    if lib_dir.is_dir():
        for py_dir in lib_dir.glob("python*"):
            posix_site = py_dir / "site-packages"
            if posix_site.is_dir():
                site_dirs.append(posix_site.resolve())
    return site_dirs


def detect_site_packages(project_root: Path) -> list[Path]:
    """Detect site-packages under project virtualenvs, falling back to sys.path."""
    site_packages_dirs: list[Path] = []
    seen: set[Path] = set()

    for venv in (project_root / ".venv", project_root / "venv"):
        if not venv.is_dir():
            continue
        for candidate in _venv_site_packages(venv):
            if candidate not in seen:
                seen.add(candidate)
                site_packages_dirs.append(candidate)

    if not site_packages_dirs:
        logger.warning(
            "No project virtualenv (.venv/venv) found under %s; "
            "falling back to the current environment.",
            project_root,
        )
        for candidate in _sys_path_site_packages():
            if candidate not in seen:
                seen.add(candidate)
                site_packages_dirs.append(candidate)

    return site_packages_dirs
