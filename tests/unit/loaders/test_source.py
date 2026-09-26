"""Tests for pyreach.loaders.source — SourceLoader and SourceFile."""

import os
from pathlib import Path

import pytest

from pyreach.exceptions import ConfigError, ParseError
from pyreach.loaders.source import SourceFile, SourceLoader


def _build_project_tree(root: Path) -> None:
    """Create a synthetic project tree for loader tests."""
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "module_a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "pkg" / "module_b.py").write_text("y = 2\n", encoding="utf-8")

    (root / "pkg" / "sub").mkdir()
    (root / "pkg" / "sub" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "sub" / "deep.py").write_text("z = 3\n", encoding="utf-8")

    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")

    (root / "venv").mkdir()
    (root / "venv" / "lib.py").write_text("# venv file\n", encoding="utf-8")

    (root / ".venv").mkdir()
    (root / ".venv" / "activate.py").write_text("# dotenv\n", encoding="utf-8")

    (root / "pkg" / "__pycache__").mkdir()
    (root / "pkg" / "__pycache__" / "module_a.cpython-310.pyc").write_bytes(b"\x00")
    (root / "pkg" / "__pycache__" / "cached.py").write_text("# cached\n", encoding="utf-8")

    (root / ".git").mkdir()
    (root / ".git" / "hook.py").write_text("# git hook\n", encoding="utf-8")

    (root / "tests").mkdir()
    (root / "tests" / "test_something.py").write_text("def test(): pass\n", encoding="utf-8")

    (root / "pkg" / "migrations").mkdir()
    (root / "pkg" / "migrations" / "001_init.py").write_text("# migration\n", encoding="utf-8")

    (root / "README.md").write_text("# Readme\n", encoding="utf-8")


class TestSourceFile:
    def test_frozen_dataclass(self) -> None:
        sf = SourceFile(path=Path("/abs/pkg/a.py"), rel_path=Path("pkg/a.py"))
        assert sf.path == Path("/abs/pkg/a.py")
        assert sf.rel_path == Path("pkg/a.py")
        with pytest.raises(AttributeError):
            sf.path = Path("/other")  # type: ignore[misc]

    def test_equality(self) -> None:
        a = SourceFile(path=Path("/x/a.py"), rel_path=Path("a.py"))
        b = SourceFile(path=Path("/x/a.py"), rel_path=Path("a.py"))
        assert a == b


class TestSourceLoaderDiscover:
    def test_discovers_py_files(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert "main.py" in rel_paths
        assert str(Path("pkg/__init__.py")) in rel_paths
        assert str(Path("pkg/module_a.py")) in rel_paths
        assert str(Path("pkg/module_b.py")) in rel_paths
        assert str(Path("pkg/sub/__init__.py")) in rel_paths
        assert str(Path("pkg/sub/deep.py")) in rel_paths

    def test_excludes_venv(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all("venv" not in p.split(os.sep)[0] for p in rel_paths)
        assert all(".venv" not in p.split(os.sep)[0] for p in rel_paths)

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all("__pycache__" not in p for p in rel_paths)

    def test_excludes_git(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all(".git" not in p.split(os.sep)[0] for p in rel_paths)

    def test_user_ignore_pattern(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path, ignore_patterns=["tests/"])
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all(not p.startswith("tests") for p in rel_paths)

    def test_user_ignore_without_trailing_slash(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path, ignore_patterns=["tests"])
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all(not p.startswith("tests") for p in rel_paths)

    def test_glob_ignore_pattern(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path, ignore_patterns=["**/migrations/*.py"])
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all("migrations" not in p for p in rel_paths)

    def test_deterministic_order(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        first = loader.discover()
        second = loader.discover()

        assert [f.rel_path for f in first] == [f.rel_path for f in second]

    def test_rel_path(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path)
        files = loader.discover()

        for sf in files:
            assert not sf.rel_path.is_absolute()
            assert sf.path.is_absolute()
            assert sf.path == (tmp_path / sf.rel_path).resolve()

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        _build_project_tree(tmp_path)
        outside = tmp_path.parent / "outside_project"
        outside.mkdir(exist_ok=True)
        evil_py = outside / "evil.py"
        evil_py.write_text("# outside\n", encoding="utf-8")

        link_dir = tmp_path / "sneaky_link"
        try:
            link_dir.symlink_to(outside)
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        loader = SourceLoader(tmp_path)
        files = loader.discover()

        abs_paths = {str(f.path) for f in files}
        assert str(evil_py.resolve()) not in abs_paths

    def test_empty_project(self, tmp_path: Path) -> None:
        loader = SourceLoader(tmp_path)
        files = loader.discover()
        assert files == []

    def test_only_non_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
        (tmp_path / "data.json").write_text("{}\n", encoding="utf-8")

        loader = SourceLoader(tmp_path)
        files = loader.discover()
        assert files == []

    def test_root_not_found_raises_config_error(self) -> None:
        loader = SourceLoader(Path("/nonexistent/root/path"))
        with pytest.raises(ConfigError):
            loader.discover()

    def test_default_excludes_cannot_be_reincluded(self, tmp_path: Path) -> None:
        """User patterns cannot override default exclusions."""
        _build_project_tree(tmp_path)
        loader = SourceLoader(tmp_path, ignore_patterns=[])
        files = loader.discover()

        rel_paths = {str(f.rel_path) for f in files}
        assert all("__pycache__" not in p for p in rel_paths)
        assert all("venv" not in p.split(os.sep)[0] for p in rel_paths)


class TestSourceLoaderRead:
    def test_read_valid_file(self, tmp_path: Path) -> None:
        py_file = tmp_path / "hello.py"
        py_file.write_text("x = 42\n", encoding="utf-8")
        sf = SourceFile(path=py_file.resolve(), rel_path=Path("hello.py"))

        loader = SourceLoader(tmp_path)
        content = loader.read(sf)
        assert content == "x = 42\n"

    def test_read_non_utf8_file_raises_parse_error(self, tmp_path: Path) -> None:
        py_file = tmp_path / "binary.py"
        py_file.write_bytes(b"\x80\x81\x82\xff\xfe")
        sf = SourceFile(path=py_file.resolve(), rel_path=Path("binary.py"))

        loader = SourceLoader(tmp_path)
        with pytest.raises(ParseError) as exc_info:
            loader.read(sf)
        assert "binary.py" in str(exc_info.value)

    def test_read_missing_file_raises_parse_error(self, tmp_path: Path) -> None:
        sf = SourceFile(
            path=(tmp_path / "gone.py").resolve(),
            rel_path=Path("gone.py"),
        )

        loader = SourceLoader(tmp_path)
        with pytest.raises(ParseError) as exc_info:
            loader.read(sf)
        assert "gone.py" in str(exc_info.value)

    def test_read_utf8_bom(self, tmp_path: Path) -> None:
        py_file = tmp_path / "bom.py"
        py_file.write_bytes(b"\xef\xbb\xbfx = 1\n")
        sf = SourceFile(path=py_file.resolve(), rel_path=Path("bom.py"))

        loader = SourceLoader(tmp_path)
        content = loader.read(sf)
        assert "x = 1" in content
