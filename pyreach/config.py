"""Strict configuration with CLI > project > user > built-in precedence."""

from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pyreach.exceptions import ConfigError


@dataclass
class Thresholds:
    fail_on_reachable: bool = True
    fail_on_potentially: bool = False


@dataclass
class PyReachConfig:
    version: str = "1"
    entry_points: list[str] = field(default_factory=list)
    ignore_paths: list[str] = field(default_factory=list)
    max_depth: int = 5
    manifest: str = "requirements.txt"
    osv_db: str = "~/.pyreach/osv.db"
    thresholds: Thresholds = field(default_factory=Thresholds)


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot load configuration {path}: {exc}") from exc
    if data is None:
        return {}
    if (
        not isinstance(data, dict)
        or set(data) != {"pyreach"}
        or not isinstance(data["pyreach"], dict)
    ):
        raise ConfigError(f"Expected a 'pyreach' mapping in {path}")
    values = data["pyreach"]
    allowed = set(PyReachConfig.__dataclass_fields__)
    if set(values) - allowed:
        raise ConfigError(f"Unknown configuration key: {sorted(set(values) - allowed)}")
    _validated(values)
    return dict(values)


def _validated(values: dict[str, Any]) -> PyReachConfig:
    config = PyReachConfig()
    for key, value in values.items():
        if key == "version":
            if str(value) != "1":
                raise ConfigError("Only configuration version 1 is supported")
            config.version = "1"
        elif key in {"entry_points", "ignore_paths"}:
            if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
                raise ConfigError(f"{key} must be a list of nonempty strings")
            setattr(config, key, list(dict.fromkeys(value)))
        elif key == "max_depth":
            if type(value) is not int or not 0 <= value <= 7:
                raise ConfigError("max_depth must be an integer in [0, 7]")
            config.max_depth = value
        elif key in {"manifest", "osv_db"}:
            if not isinstance(value, str) or not value:
                raise ConfigError(f"{key} must be a nonempty path")
            setattr(config, key, value)
        elif key == "thresholds":
            if not isinstance(value, dict) or set(value) - set(Thresholds.__dataclass_fields__):
                raise ConfigError("Unknown thresholds key or invalid thresholds mapping")
            if any(type(x) is not bool for x in value.values()):
                raise ConfigError("Threshold values must be booleans")
            config.thresholds = Thresholds(**value)
    config.osv_db = str(Path(config.osv_db).expanduser())
    return config


def _project_file(root: Path) -> Path:
    for name in (".pyreach.yml", ".pyreach.yaml"):
        if (root / name).exists():
            return root / name
    return root / ".pyreach.yml"


def load_config(project_root: Path) -> PyReachConfig | None:
    path = _project_file(project_root)
    return _validated(_read(path)) if path.is_file() else None


def resolve_config(cli_args: Namespace, project_root: Path) -> PyReachConfig:
    values: dict[str, Any] = {}
    for layer in (_read(Path.home() / ".pyreach/config.yml"), _read(_project_file(project_root))):
        for key, value in layer.items():
            if key in {"entry_points", "ignore_paths"}:
                values[key] = list(dict.fromkeys([*values.get(key, []), *value]))
            elif key == "thresholds":
                values[key] = {**values.get(key, {}), **value}
            else:
                values[key] = value
    for flag, key in (("manifest", "manifest"), ("db_path", "osv_db"), ("max_depth", "max_depth")):
        value = getattr(cli_args, flag, None)
        if value is not None:
            values[key] = value
    for flag, key in (("entry_point", "entry_points"), ("exclude", "ignore_paths")):
        values[key] = list(dict.fromkeys([*values.get(key, []), *getattr(cli_args, flag, [])]))
    config = _validated(values)
    if getattr(cli_args, "include_potentially", False):
        config.thresholds.fail_on_potentially = True
    if getattr(cli_args, "no_fail", False):
        config.thresholds = Thresholds(False, False)
    return config
