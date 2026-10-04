"""Tests for pyreach.loaders.packages — PackageResolver and InstalledPackage."""

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from pyreach.loaders.packages import (
    InstalledPackage,
    PackageResolver,
    detect_site_packages,
)
from pyreach.parsers.manifest import Dependency


def _create_mock_distribution(
    site_packages: Path,
    dist_name: str,
    version: str,
    top_level: list[str] | None = None,
    files: list[str] | None = None,
    direct_url: dict[str, object] | None = None,
) -> Path:
    """Helper to create a fake .dist-info directory in a mock site-packages."""
    dist_info = site_packages / f"{dist_name}-{version}.dist-info"
    dist_info.mkdir(parents=True, exist_ok=True)

    metadata_content = f"Metadata-Version: 2.1\nName: {dist_name}\nVersion: {version}\n"
    (dist_info / "METADATA").write_text(metadata_content, encoding="utf-8")

    if top_level is not None:
        (dist_info / "top_level.txt").write_text("\n".join(top_level) + "\n", encoding="utf-8")

    if files is not None:
        (dist_info / "RECORD").write_text(
            "\n".join(f"{f},," for f in files) + "\n", encoding="utf-8"
        )

    if direct_url is not None:
        (dist_info / "direct_url.json").write_text(json.dumps(direct_url), encoding="utf-8")

    return dist_info


class TestInstalledPackage:
    def test_frozen_dataclass(self) -> None:
        pkg = InstalledPackage(
            name="requests",
            version="2.31.0",
            location=Path("/site-packages"),
            top_level=["requests"],
        )
        assert pkg.name == "requests"
        assert pkg.version == "2.31.0"
        assert pkg.location == Path("/site-packages")
        assert pkg.top_level == ["requests"]
        with pytest.raises(AttributeError):
            pkg.name = "other"  # type: ignore[misc]

    def test_equality(self) -> None:
        p1 = InstalledPackage("foo", "1.0", Path("/site"), ["foo"])
        p2 = InstalledPackage("foo", "1.0", Path("/site"), ["foo"])
        assert p1 == p2


class TestPackageResolver:
    def test_resolve_installed_real_env(self) -> None:
        """Resolve packages known to be installed in the test virtual environment."""
        resolver = PackageResolver()
        # networkx and packaging are in pyproject.toml dependencies
        pkg = resolver.resolve("packaging")
        assert pkg is not None
        assert pkg.name == "packaging"
        assert pkg.version != ""
        assert pkg.location.exists()
        assert "packaging" in pkg.top_level

    def test_missing_package_returns_none(self) -> None:
        resolver = PackageResolver()
        assert resolver.resolve("completely-nonexistent-package-xyz-123") is None

    def test_name_normalization(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        _create_mock_distribution(site, "Foo_Bar.Baz", "1.2.3", top_level=["foobarbaz"])

        resolver = PackageResolver(search_paths=[site])
        # Should resolve regardless of case or separators
        p1 = resolver.resolve("foo-bar-baz")
        p2 = resolver.resolve("Foo_Bar.Baz")
        p3 = resolver.resolve("FOO_BAR-BAZ")

        assert p1 is not None
        assert p1 == p2 == p3
        assert p1.name == "foo-bar-baz"
        assert p1.version == "1.2.3"
        assert p1.top_level == ["foobarbaz"]

    def test_top_level_inference_without_txt(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        _create_mock_distribution(
            site,
            "my_lib",
            "0.1.0",
            top_level=None,
            files=[
                "my_lib/__init__.py",
                "my_lib/core.py",
                "single_mod.py",
                "my_lib-0.1.0.dist-info/METADATA",
                "my_lib-0.1.0.dist-info/RECORD",
            ],
        )

        resolver = PackageResolver(search_paths=[site])
        pkg = resolver.resolve("my-lib")
        assert pkg is not None
        assert "my_lib" in pkg.top_level
        assert "single_mod" in pkg.top_level

    def test_top_level_fallback_to_name(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        _create_mock_distribution(
            site,
            "fallback_pkg",
            "1.0.0",
            top_level=None,
            files=None,
        )

        resolver = PackageResolver(search_paths=[site])
        pkg = resolver.resolve("fallback-pkg")
        assert pkg is not None
        assert pkg.top_level == ["fallback_pkg"]

    def test_editable_install_direct_url(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        src_dir = tmp_path / "src" / "my_editable"
        src_dir.mkdir(parents=True)

        url_str = src_dir.as_uri()
        _create_mock_distribution(
            site,
            "editable_pkg",
            "0.5.0",
            top_level=["editable_pkg"],
            direct_url={"url": url_str, "dir_info": {"editable": True}},
        )

        resolver = PackageResolver(search_paths=[site])
        pkg = resolver.resolve("editable-pkg")
        assert pkg is not None
        assert pkg.name == "editable-pkg"
        assert pkg.location == src_dir.resolve()

    def test_editable_install_egg_link(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        src_dir = tmp_path / "src" / "legacy_editable"
        src_dir.mkdir(parents=True)

        _create_mock_distribution(
            site,
            "legacy_pkg",
            "1.0.0",
            top_level=["legacy_pkg"],
        )
        (site / "legacy_pkg.egg-link").write_text(f"{src_dir}\n", encoding="utf-8")

        resolver = PackageResolver(search_paths=[site])
        pkg = resolver.resolve("legacy-pkg")
        assert pkg is not None
        assert pkg.location == src_dir.resolve()

    def test_resolve_all_mixed(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        _create_mock_distribution(site, "pkg_one", "1.0.0", top_level=["pkg_one"])
        _create_mock_distribution(site, "pkg_two", "2.0.0", top_level=["pkg_two"])

        resolver = PackageResolver(search_paths=[site])
        deps = [
            Dependency(name="pkg-one", version="1.0.0", source="requirements.txt"),
            Dependency(name="missing-pkg", version="3.0.0", source="requirements.txt"),
            Dependency(name="pkg-two", version="2.0.0", source="requirements.txt"),
        ]

        resolved = resolver.resolve_all(deps)
        assert len(resolved) == 2
        assert "pkg-one" in resolved
        assert "pkg-two" in resolved
        assert "missing-pkg" not in resolved
        assert resolved["pkg-one"].version == "1.0.0"

    def test_cache_reuse(self, tmp_path: Path) -> None:
        site = tmp_path / "site-packages"
        site.mkdir()
        _create_mock_distribution(site, "cached_pkg", "1.0.0", top_level=["cached_pkg"])

        resolver = PackageResolver(search_paths=[site])

        with patch.object(resolver, "_get_distributions", wraps=resolver._get_distributions) as spy:
            pkg1 = resolver.resolve("cached-pkg")
            pkg2 = resolver.resolve("cached-pkg")
            assert pkg1 is not None
            assert pkg1 == pkg2
            # Distributions should be enumerated only on initial load
            assert spy.call_count == 1


class TestDetectSitePackages:
    def test_detect_windows_structure(self, tmp_path: Path) -> None:
        project_root = tmp_path / "my_project"
        site = project_root / ".venv" / "Lib" / "site-packages"
        site.mkdir(parents=True)

        found = detect_site_packages(project_root)
        assert len(found) >= 1
        assert site.resolve() in [p.resolve() for p in found]

    def test_detect_posix_structure(self, tmp_path: Path) -> None:
        project_root = tmp_path / "my_project"
        site = project_root / "venv" / "lib" / "python3.10" / "site-packages"
        site.mkdir(parents=True)

        found = detect_site_packages(project_root)
        assert len(found) >= 1
        assert site.resolve() in [p.resolve() for p in found]

    def test_detect_no_venv_falls_back_to_sys_path(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        project_root = tmp_path / "bare_project"
        project_root.mkdir()
        with caplog.at_level(logging.WARNING):
            found = detect_site_packages(project_root)
        assert found  # falls back to the current environment's site-packages
        assert any("falling back" in record.message for record in caplog.records)
