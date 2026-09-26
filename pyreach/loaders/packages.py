"""Installed package resolver mapping dependency names to site-packages paths."""

from __future__ import annotations

import importlib.metadata
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pyreach.parsers.manifest import normalize_name

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyreach.parsers.manifest import Dependency


@dataclass(frozen=True)
class InstalledPackage:
    """An installed Python package discovered in a virtual environment or site-packages."""

    name: str  # normalized distribution name (PEP 503)
    version: str
    location: Path  # directory containing the importable package or editable source
    top_level: list[str]  # list of top-level importable module or package names


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

    def _load_cache(self) -> dict[str, InstalledPackage]:
        if self._cache is not None:
            return self._cache

        cache: dict[str, InstalledPackage] = {}
        for dist in self._get_distributions():
            raw_name: str | None = None
            if dist.metadata and "Name" in dist.metadata:
                raw_name = dist.metadata["Name"]
            if not raw_name:
                continue

            norm_name = normalize_name(raw_name)
            version = dist.version or ""

            # Determine package location (handle editable installs if present)
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

            # Determine top-level modules
            top_level: list[str] = []
            top_level_text = dist.read_text("top_level.txt")
            if top_level_text:
                top_level = [line.strip() for line in top_level_text.splitlines() if line.strip()]

            if not top_level:
                record_text = dist.read_text("RECORD")
                if record_text:
                    inferred: set[str] = set()
                    for line in record_text.splitlines():
                        if not line.strip():
                            continue
                        file_rel = line.split(",")[0].strip()
                        parts = Path(file_rel).parts
                        if not parts or parts[0].endswith((".dist-info", ".egg-info")):
                            continue
                        if len(parts) >= 2 and parts[1] == "__init__.py":
                            inferred.add(parts[0])
                        elif len(parts) == 1 and parts[0].endswith(".py"):
                            inferred.add(parts[0][:-3])
                    if inferred:
                        top_level = sorted(inferred)

            if not top_level and dist.files:
                inferred_files: set[str] = set()
                for file_path in dist.files:
                    parts = file_path.parts
                    if not parts or parts[0].endswith((".dist-info", ".egg-info")):
                        continue
                    if len(parts) >= 2 and parts[1] == "__init__.py":
                        inferred_files.add(parts[0])
                    elif len(parts) == 1 and parts[0].endswith(".py"):
                        inferred_files.add(parts[0][:-3])
                if inferred_files:
                    top_level = sorted(inferred_files)

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


def detect_site_packages(project_root: Path) -> list[Path]:
    """Detect site-packages directories under project virtualenvs (.venv or venv)."""
    candidates = [
        project_root / ".venv",
        project_root / "venv",
    ]

    site_packages_dirs: list[Path] = []
    seen: set[Path] = set()

    for venv in candidates:
        if not venv.is_dir():
            continue

        # Windows layout: Lib/site-packages
        win_site = venv / "Lib" / "site-packages"
        if win_site.is_dir():
            resolved = win_site.resolve()
            if resolved not in seen:
                seen.add(resolved)
                site_packages_dirs.append(resolved)

        # Lowercase lib/site-packages
        win_site_lower = venv / "lib" / "site-packages"
        if win_site_lower.is_dir():
            resolved = win_site_lower.resolve()
            if resolved not in seen:
                seen.add(resolved)
                site_packages_dirs.append(resolved)

        # POSIX layout: lib/pythonX.Y/site-packages
        lib_dir = venv / "lib"
        if lib_dir.is_dir():
            for py_dir in lib_dir.glob("python*"):
                posix_site = py_dir / "site-packages"
                if posix_site.is_dir():
                    resolved = posix_site.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        site_packages_dirs.append(resolved)

    return site_packages_dirs
