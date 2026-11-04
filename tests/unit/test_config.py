"""Configuration trust boundaries and override contracts."""

from argparse import Namespace
from pathlib import Path

import pytest

from pyreach.config import load_config, resolve_config
from pyreach.exceptions import ConfigError


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
def test_rejects_invalid_config(tmp_path, body):
    (tmp_path / ".pyreach.yml").write_text(body)
    with pytest.raises(ConfigError):
        load_config(tmp_path)


def test_precedence_and_additive_lists(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".pyreach").mkdir()
    (home / ".pyreach/config.yml").write_text(
        "pyreach:\n  max_depth: 2\n  entry_points: [a]\n  ignore_paths: [tests/]\n"
        "  thresholds:\n    fail_on_reachable: false\n"
    )
    monkeypatch.setattr(Path, "home", lambda: home)
    project = tmp_path / "project"
    project.mkdir()
    (project / ".pyreach.yaml").write_text(
        "pyreach:\n  max_depth: 3\n  entry_points: [b]\n"
        "  thresholds:\n    fail_on_potentially: true\n"
    )
    c = resolve_config(Namespace(max_depth=5, entry_point=["c"], exclude=["docs/"]), project)
    assert c.max_depth == 5 and c.entry_points == ["a", "b", "c"]
    assert c.ignore_paths == ["tests/", "docs/"]
    assert c.thresholds.fail_on_potentially and not c.thresholds.fail_on_reachable
    assert not resolve_config(Namespace(no_fail=True), project).thresholds.fail_on_potentially


def test_defaults_and_empty_config(tmp_path):
    assert load_config(tmp_path) is None
    (tmp_path / ".pyreach.yml").write_text("")
    assert load_config(tmp_path).max_depth == 5
    assert resolve_config(Namespace(), tmp_path).max_depth == 5
