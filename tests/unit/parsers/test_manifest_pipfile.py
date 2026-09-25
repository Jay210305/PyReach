import json
from pathlib import Path

import pytest

from pyreach.exceptions import ConfigError, ParseError
from pyreach.parsers.manifest import (
    SOURCE_PIPFILE_LOCK,
    ManifestParser,
    PipfileLockParser,
    RequirementsTxtParser,
    select_manifest_parser,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "manifests"


def _write_lock(tmp_path: Path, data: object) -> Path:
    p = tmp_path / "Pipfile.lock"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_pipfile_parser_implements_protocol() -> None:
    parser = PipfileLockParser()
    assert isinstance(parser, ManifestParser)
    assert parser.source_name == SOURCE_PIPFILE_LOCK
    assert parser.supports(Path("Pipfile.lock")) is True
    assert parser.supports(Path("sub/Pipfile.lock")) is True
    assert parser.supports(Path("requirements.txt")) is False


def test_parse_default_section() -> None:
    fixture_path = FIXTURES_DIR / "Pipfile.lock"
    deps = PipfileLockParser().parse(fixture_path)
    assert len(deps) == 3
    # Sorted alphabetically
    names = [d.name for d in deps]
    assert names == ["flask", "requests", "urllib3"]


def test_parse_develop_excluded_by_default() -> None:
    fixture_path = FIXTURES_DIR / "Pipfile.lock"
    deps = PipfileLockParser(include_dev=False).parse(fixture_path)
    names = [d.name for d in deps]
    assert "pytest" not in names


def test_parse_develop_included() -> None:
    fixture_path = FIXTURES_DIR / "Pipfile.lock"
    deps = PipfileLockParser(include_dev=True).parse(fixture_path)
    names = [d.name for d in deps]
    assert "pytest" in names
    pytest_dep = next(d for d in deps if d.name == "pytest")
    assert pytest_dep.version == "7.4.0"
    assert pytest_dep.source == SOURCE_PIPFILE_LOCK


def test_version_operator_stripped(tmp_path: Path) -> None:
    data = {
        "default": {
            "pkg1": {"version": "==2.31.0"},
            "pkg2": {"version": ">=1.0.0"},
            "pkg3": {"version": "~=3.2.1"},
            "pkg4": {},
        }
    }
    p = _write_lock(tmp_path, data)
    deps = PipfileLockParser().parse(p)
    dep_map = {d.name: d.version for d in deps}
    assert dep_map["pkg1"] == "2.31.0"
    assert dep_map["pkg2"] == "1.0.0"
    assert dep_map["pkg3"] == "3.2.1"
    assert dep_map["pkg4"] == ""


def test_marker_preserved(tmp_path: Path) -> None:
    data = {
        "default": {
            "urllib3": {
                "version": "==2.0.4",
                "markers": "python_version >= '3.10'",
            }
        }
    }
    p = _write_lock(tmp_path, data)
    deps = PipfileLockParser().parse(p)
    assert len(deps) == 1
    assert deps[0].marker == "python_version >= '3.10'"


def test_extras_preserved(tmp_path: Path) -> None:
    data = {
        "default": {
            "requests": {
                "version": "==2.31.0",
                "extras": ["security", "socks"],
            }
        }
    }
    p = _write_lock(tmp_path, data)
    deps = PipfileLockParser().parse(p)
    assert len(deps) == 1
    assert deps[0].extra == "security,socks"


def test_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.lock"
    with pytest.raises(ConfigError) as exc_info:
        PipfileLockParser().parse(missing)
    assert str(missing) in str(exc_info.value)


def test_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "Pipfile.lock"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        PipfileLockParser().parse(p)
    assert "Invalid JSON" in str(exc_info.value)


def test_missing_default_section(tmp_path: Path) -> None:
    p = _write_lock(tmp_path, {"_meta": {}})
    deps = PipfileLockParser().parse(p)
    assert deps == []


def test_source_field(tmp_path: Path) -> None:
    p = _write_lock(tmp_path, {"default": {"requests": {"version": "==2.31.0"}}})
    deps = PipfileLockParser().parse(p)
    assert len(deps) == 1
    assert deps[0].source == SOURCE_PIPFILE_LOCK


def test_top_level_not_dict(tmp_path: Path) -> None:
    p = tmp_path / "Pipfile.lock"
    p.write_text('["item1", "item2"]', encoding="utf-8")
    with pytest.raises(ParseError) as exc_info:
        PipfileLockParser().parse(p)
    assert "Expected JSON object" in str(exc_info.value)


def test_non_pypi_skipped_or_included(tmp_path: Path) -> None:
    data = {
        "default": {
            "normal_pkg": {"version": "==1.0.0"},
            "git_pkg": {"git": "https://github.com/org/repo.git", "ref": "v1.0"},
            "path_pkg": {"path": "./local_pkg"},
        }
    }
    p = _write_lock(tmp_path, data)

    default_deps = PipfileLockParser(include_non_pypi=False).parse(p)
    assert [d.name for d in default_deps] == ["normal-pkg"]

    all_deps = PipfileLockParser(include_non_pypi=True).parse(p)
    assert [d.name for d in all_deps] == ["git-pkg", "normal-pkg", "path-pkg"]


def test_select_manifest_parser(tmp_path: Path) -> None:
    assert select_manifest_parser(tmp_path) is None

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("requests==2.31.0\n", encoding="utf-8")
    parser = select_manifest_parser(tmp_path)
    assert isinstance(parser, RequirementsTxtParser)

    pip_file = tmp_path / "Pipfile.lock"
    pip_file.write_text("{}", encoding="utf-8")
    # Prefers requirements.txt when both exist
    parser_both = select_manifest_parser(tmp_path)
    assert isinstance(parser_both, RequirementsTxtParser)

    req_file.unlink()
    # Falls back to Pipfile.lock
    parser_pip = select_manifest_parser(tmp_path)
    assert isinstance(parser_pip, PipfileLockParser)


def test_parse_malformed_fixture() -> None:
    malformed_file = FIXTURES_DIR / "Pipfile.malformed.lock"
    with pytest.raises(ParseError) as exc_info:
        PipfileLockParser().parse(malformed_file)
    assert "Invalid JSON" in str(exc_info.value)


def test_conftest_pipfile_fixture(sample_pipfile_lock: Path) -> None:
    deps = PipfileLockParser().parse(sample_pipfile_lock)
    assert len(deps) == 2
    names = [d.name for d in deps]
    assert names == ["flask", "requests"]
