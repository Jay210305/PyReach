"""Unit tests for `.pyreach.yml` loading and CLI precedence (S4-T5)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from pyreach.config import PyReachConfig, load_config, load_user_config, resolve_config
from pyreach.exceptions import ConfigError

FULL_CONFIG = """\
pyreach:
  version: "1"
  entry_points:
    - "myapp.cli:main"
  ignore_paths:
    - "tests/"
  max_depth: 3
  manifest: "deps/requirements.txt"
  osv_db: "~/custom-osv.db"
  thresholds:
    fail_on_reachable: true
    fail_on_potentially: true
"""


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def _ns(**overrides: object) -> argparse.Namespace:
    base = {
        "manifest": None,
        "db_path": None,
        "entry_point": None,
        "max_depth": None,
        "exclude": None,
        "include_potentially": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _write(project: Path, text: str, name: str = ".pyreach.yml") -> Path:
    path = project / name
    path.write_text(text, encoding="utf-8")
    return path


def test_load_valid_config(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = load_config(tmp_path)
    assert cfg is not None
    assert cfg.version == "1"
    assert cfg.entry_points == ["myapp.cli:main"]
    assert cfg.ignore_paths == ["tests/"]
    assert cfg.max_depth == 3
    assert cfg.manifest == "deps/requirements.txt"
    assert cfg.osv_db.endswith("custom-osv.db") and "~" not in cfg.osv_db
    assert cfg.thresholds.fail_on_reachable is True
    assert cfg.thresholds.fail_on_potentially is True


def test_load_sample_fixture() -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "sample-config"
    cfg = load_config(fixture)
    assert cfg is not None
    assert cfg.max_depth == 3
    assert "myapp.cli:main" in cfg.entry_points
    assert "tests/" in cfg.ignore_paths


def test_missing_config_returns_none(tmp_path: Path) -> None:
    assert load_config(tmp_path) is None
    assert load_user_config(tmp_path / "home") is None


def test_flat_unknown_key_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "max_depth: 2\nbogus: 1\n")
    with pytest.raises(ConfigError, match="bogus"):
        load_config(tmp_path)


def test_yaml_extension_fallback(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: 2\n", name=".pyreach.yaml")
    cfg = load_config(tmp_path)
    assert cfg is not None
    assert cfg.max_depth == 2


def test_empty_file_uses_defaults(tmp_path: Path) -> None:
    _write(tmp_path, "")
    assert load_config(tmp_path) == PyReachConfig()


def test_malformed_yaml_raises_config_error(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: [unclosed\n")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_unknown_key_raises_config_error(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  bogus_key: 1\n")
    with pytest.raises(ConfigError, match="bogus_key"):
        load_config(tmp_path)


def test_unknown_threshold_key_raises_config_error(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  thresholds:\n    fail_on_maybe: true\n")
    with pytest.raises(ConfigError, match="fail_on_maybe"):
        load_config(tmp_path)


def test_bad_max_depth_type(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: deep\n")
    with pytest.raises(ConfigError, match="max_depth"):
        load_config(tmp_path)


def test_negative_max_depth_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: -1\n")
    with pytest.raises(ConfigError, match="max_depth"):
        load_config(tmp_path)


def test_max_depth_above_cap_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: 8\n")
    with pytest.raises(ConfigError, match="max_depth"):
        load_config(tmp_path)


def test_bad_entry_points_type(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  entry_points: myapp.main\n")
    with pytest.raises(ConfigError, match="entry_points"):
        load_config(tmp_path)


def test_top_level_list_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "- just\n- a\n- list\n")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(tmp_path)


def test_pyreach_with_siblings_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  max_depth: 2\nversion: '1'\n")
    with pytest.raises(ConfigError, match="sole top-level"):
        load_config(tmp_path)


def test_flat_shape_accepted(tmp_path: Path) -> None:
    _write(tmp_path, "max_depth: 2\nentry_points:\n  - a.b\n")
    cfg = load_config(tmp_path)
    assert cfg is not None
    assert cfg.max_depth == 2
    assert cfg.entry_points == ["a.b"]


def test_bad_manifest_and_threshold_types(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  manifest: 42\n")
    with pytest.raises(ConfigError, match="manifest"):
        load_config(tmp_path)
    _write(tmp_path, "pyreach:\n  osv_db: 42\n")
    with pytest.raises(ConfigError, match="osv_db"):
        load_config(tmp_path)
    _write(tmp_path, "pyreach:\n  thresholds: []\n")
    with pytest.raises(ConfigError, match="thresholds"):
        load_config(tmp_path)
    _write(tmp_path, "pyreach:\n  thresholds:\n    fail_on_reachable: yes-please\n")
    with pytest.raises(ConfigError, match="fail_on_reachable"):
        load_config(tmp_path)


def test_version_int_coerced(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  version: 1\n")
    cfg = load_config(tmp_path)
    assert cfg is not None
    assert cfg.version == "1"


def test_unsupported_version_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "pyreach:\n  version: '2'\n")
    with pytest.raises(ConfigError, match="version"):
        load_config(tmp_path)


def test_cli_overrides_config(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(
        _ns(max_depth=7, manifest="other.txt", db_path=str(tmp_path / "x.db")),
        tmp_path,
    )
    assert cfg.max_depth == 7
    assert cfg.manifest == "other.txt"
    assert cfg.osv_db == str(tmp_path / "x.db")


def test_config_used_when_cli_absent(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(_ns(), tmp_path)
    assert cfg.max_depth == 3
    assert cfg.manifest == "deps/requirements.txt"
    assert cfg.osv_db.endswith("custom-osv.db")


def test_entry_points_union(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(_ns(entry_point=["extra.entry"]), tmp_path)
    assert cfg.entry_points == ["myapp.cli:main", "extra.entry"]


def test_exclude_union(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(_ns(exclude=["scripts/"]), tmp_path)
    assert cfg.ignore_paths == ["tests/", "scripts/"]


def test_tilde_expansion(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(_ns(), tmp_path)
    assert "~" not in cfg.osv_db
    assert cfg.osv_db.endswith("custom-osv.db")


def test_thresholds_mapping(tmp_path: Path) -> None:
    _write(tmp_path, FULL_CONFIG)
    cfg = resolve_config(_ns(), tmp_path)
    assert cfg.thresholds.fail_on_potentially is True
    plain = resolve_config(_ns(), tmp_path.parent)
    assert plain.thresholds.fail_on_potentially is False


def test_cli_include_potentially_forces_flag(tmp_path: Path) -> None:
    cfg = resolve_config(_ns(include_potentially=True), tmp_path)
    assert cfg.thresholds.fail_on_potentially is True


def test_defaults_when_no_cli_no_config(tmp_path: Path) -> None:
    assert resolve_config(_ns(), tmp_path) == PyReachConfig()


def test_project_beats_user_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = Path.home() / ".pyreach"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yml").write_text("pyreach:\n  max_depth: 6\n", encoding="utf-8")
    assert load_user_config() is not None
    assert resolve_config(_ns(), tmp_path).max_depth == 6
    _write(tmp_path, "pyreach:\n  max_depth: 2\n")
    assert resolve_config(_ns(), tmp_path).max_depth == 2


def test_partial_project_config_keeps_user_values(tmp_path: Path) -> None:
    home = Path.home() / ".pyreach"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yml").write_text(
        "pyreach:\n  max_depth: 6\n  manifest: global.txt\n", encoding="utf-8"
    )
    _write(tmp_path, "pyreach:\n  entry_points:\n    - a.b\n")
    cfg = resolve_config(_ns(), tmp_path)
    assert cfg.max_depth == 6
    assert cfg.manifest == "global.txt"
    assert cfg.entry_points == ["a.b"]


@pytest.mark.parametrize(
    "body",
    [
        "[bad]",
        "pyreach: []",
        "pyreach:\n  nope: 1",
        "pyreach:\n  max_depth: true",
        "pyreach:\n  max_depth: 8",
        "pyreach:\n  entry_points: [1]",
        "pyreach:\n  thresholds:\n    fail_on_reachable: yesplease",
        "pyreach:\n  manifest: 2",
        "pyreach:\n  version: 3",
        "pyreach:\n  thresholds:\n    bad: true",
    ],
)
def test_rejects_invalid_config(tmp_path: Path, body: str) -> None:
    (tmp_path / ".pyreach.yml").write_text(body, encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_precedence_and_additive_lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    (home / ".pyreach").mkdir(exist_ok=True)
    (home / ".pyreach/config.yml").write_text(
        "pyreach:\n  max_depth: 2\n  entry_points: [a]\n  ignore_paths: [tests/]\n"
        "  thresholds:\n    fail_on_reachable: false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".pyreach.yaml").write_text(
        "pyreach:\n  max_depth: 3\n  entry_points: [b]\n"
        "  thresholds:\n    fail_on_potentially: true\n",
        encoding="utf-8",
    )
    c = resolve_config(
        argparse.Namespace(max_depth=5, entry_point=["c"], exclude=["docs/"]), project, home=home
    )
    assert c.max_depth == 5 and c.entry_points == ["a", "b", "c"]
    assert c.ignore_paths == ["tests/", "docs/"]
    assert c.thresholds.fail_on_potentially and not c.thresholds.fail_on_reachable
    assert not resolve_config(
        argparse.Namespace(no_fail=True), project, home=home
    ).thresholds.fail_on_potentially


def test_defaults_and_empty_config(tmp_path: Path) -> None:
    assert load_config(tmp_path) is None
    (tmp_path / ".pyreach.yml").write_text("", encoding="utf-8")
    assert load_config(tmp_path).max_depth == 5
    assert resolve_config(argparse.Namespace(), tmp_path).max_depth == 5
