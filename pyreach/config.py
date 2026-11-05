"""Project and user configuration (S4-T5).

Loads ``.pyreach.yml`` (project) and ``~/.pyreach/config.yml`` (user-global)
and merges them with CLI flags. Precedence (highest first): CLI flags >
project config > user-global config > built-in defaults.

The module is isolated behind :func:`load_config` / :func:`resolve_config`
so the feature can be removed (scope cut #3) by making ``load_config``
return ``None``.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pyreach.exceptions import ConfigError

logger = logging.getLogger(__name__)

CONFIG_FILENAMES = (".pyreach.yml", ".pyreach.yaml")
USER_CONFIG_FILENAMES = ("config.yml", "config.yaml")
USER_CONFIG_DIRNAME = ".pyreach"
SUPPORTED_VERSIONS = frozenset({"1"})
MAX_SCAN_DEPTH = 7

_TOP_LEVEL_KEYS = frozenset(
    {
        "version",
        "entry_points",
        "ignore_paths",
        "max_depth",
        "manifest",
        "osv_db",
        "thresholds",
    }
)
_THRESHOLD_KEYS = frozenset({"fail_on_reachable", "fail_on_potentially"})


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


def _find_file(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"Invalid config in {path}: top level must be a mapping.")
    if "pyreach" in data:
        if set(data) != {"pyreach"} or not isinstance(data["pyreach"], dict):
            raise ConfigError(
                f"Invalid config in {path}: 'pyreach' must be the sole top-level mapping."
            )
        return dict(data["pyreach"])
    unknown_top = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown_top:
        raise ConfigError(f"Unknown config key(s) in {path}: {', '.join(unknown_top)}.")
    return {k: v for k, v in data.items() if k in _TOP_LEVEL_KEYS}


def _as_str_list(value: Any, key: str, path: Path) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(f"Invalid config in {path}: '{key}' must be a list of strings.")
    return list(value)


def _build_config(data: dict[str, Any], path: Path) -> tuple[PyReachConfig, set[str]]:
    unknown = sorted(set(data) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ConfigError(f"Unknown config key(s) in {path}: {', '.join(unknown)}.")
    cfg = PyReachConfig()
    fields: set[str] = set()

    if "version" in data:
        cfg.version = str(data["version"])
        fields.add("version")
        if cfg.version not in SUPPORTED_VERSIONS:
            raise ConfigError(f"Unsupported config version in {path}: {cfg.version!r}.")
    if "entry_points" in data:
        cfg.entry_points = _as_str_list(data["entry_points"], "entry_points", path)
        fields.add("entry_points")
    if "ignore_paths" in data:
        cfg.ignore_paths = _as_str_list(data["ignore_paths"], "ignore_paths", path)
        fields.add("ignore_paths")
    if "max_depth" in data:
        depth = data["max_depth"]
        if isinstance(depth, bool) or not isinstance(depth, int):
            raise ConfigError(f"Invalid config in {path}: 'max_depth' must be an integer.")
        if depth < 0 or depth > MAX_SCAN_DEPTH:
            raise ConfigError(
                f"Invalid config in {path}: 'max_depth' must be in [0, {MAX_SCAN_DEPTH}]."
            )
        cfg.max_depth = depth
        fields.add("max_depth")
    if "manifest" in data:
        if not isinstance(data["manifest"], str):
            raise ConfigError(f"Invalid config in {path}: 'manifest' must be a string.")
        cfg.manifest = data["manifest"]
        fields.add("manifest")
    if "osv_db" in data:
        if not isinstance(data["osv_db"], str):
            raise ConfigError(f"Invalid config in {path}: 'osv_db' must be a string.")
        cfg.osv_db = str(Path(data["osv_db"]).expanduser())
        fields.add("osv_db")
    if "thresholds" in data:
        raw = data["thresholds"]
        if not isinstance(raw, dict):
            raise ConfigError(f"Invalid config in {path}: 'thresholds' must be a mapping.")
        unknown_thresholds = sorted(set(raw) - _THRESHOLD_KEYS)
        if unknown_thresholds:
            raise ConfigError(
                f"Unknown thresholds key(s) in {path}: {', '.join(unknown_thresholds)}."
            )
        for key in _THRESHOLD_KEYS:
            if key in raw:
                if not isinstance(raw[key], bool):
                    raise ConfigError(
                        f"Invalid config in {path}: 'thresholds.{key}' must be true/false."
                    )
                setattr(cfg.thresholds, key, raw[key])
                fields.add(f"thresholds.{key}")
    return cfg, fields


def _parse_file(path: Path) -> tuple[PyReachConfig, set[str]]:
    return _build_config(_read_mapping(path), path)


def load_config(project_root: Path) -> PyReachConfig | None:
    """Load ``<project_root>/.pyreach.yml`` (or ``.yaml``).

    Returns ``None`` when no config file exists. Raises :class:`ConfigError`
    on malformed content or unknown keys.
    """
    found = _find_file(Path(project_root), CONFIG_FILENAMES)
    if found is None:
        return None
    cfg, _fields = _parse_file(found)
    return cfg


def _load_user_file(home: Path | None = None) -> tuple[PyReachConfig, set[str]] | None:
    """Return the parsed user-global config and its explicitly-set fields."""
    base = Path(home).expanduser() if home is not None else Path("~").expanduser()
    found = _find_file(base / USER_CONFIG_DIRNAME, USER_CONFIG_FILENAMES)
    if found is None:
        return None
    return _parse_file(found)


def load_user_config(home: Path | None = None) -> PyReachConfig | None:
    """Load the user-global ``~/.pyreach/config.yml`` (or ``.yaml``)."""
    result = _load_user_file(home)
    return result[0] if result is not None else None


def _overlay(base: PyReachConfig, over: PyReachConfig, fields: set[str]) -> PyReachConfig:
    if "version" in fields:
        base.version = over.version
    if "entry_points" in fields:
        for ep in over.entry_points:
            if ep not in base.entry_points:
                base.entry_points.append(ep)
    if "ignore_paths" in fields:
        for ip in over.ignore_paths:
            if ip not in base.ignore_paths:
                base.ignore_paths.append(ip)
    if "max_depth" in fields:
        base.max_depth = over.max_depth
    if "manifest" in fields:
        base.manifest = over.manifest
    if "osv_db" in fields:
        base.osv_db = over.osv_db
    if "thresholds.fail_on_reachable" in fields:
        base.thresholds.fail_on_reachable = over.thresholds.fail_on_reachable
    if "thresholds.fail_on_potentially" in fields:
        base.thresholds.fail_on_potentially = over.thresholds.fail_on_potentially
    return base


def resolve_config(
    cli_args: argparse.Namespace, project_root: Path, home: Path | None = None
) -> PyReachConfig:
    """Merge defaults <- user-global <- project <- CLI flags into one config.

    Only CLI flags explicitly provided (parser defaults are ``None``) override
    file values. ``entry_points``/``ignore_paths`` are additive unions;
    ``--include-potentially`` ORs with ``thresholds.fail_on_potentially``.
    ``home`` overrides the user-global config root (defaults to ``~``).
    """
    merged = PyReachConfig()
    user = _load_user_file(home)
    if user is not None:
        user_cfg, user_fields = user
        merged = _overlay(merged, user_cfg, user_fields)
    project_file = _find_file(Path(project_root), CONFIG_FILENAMES)
    if project_file is not None:
        project_cfg, project_fields = _parse_file(project_file)
        merged = _overlay(merged, project_cfg, project_fields)

    manifest = getattr(cli_args, "manifest", None)
    if manifest is not None:
        merged.manifest = manifest
    db_path = getattr(cli_args, "db_path", None)
    if db_path is not None:
        merged.osv_db = db_path
    max_depth = getattr(cli_args, "max_depth", None)
    if max_depth is not None:
        merged.max_depth = max_depth
    for entry in getattr(cli_args, "entry_point", None) or []:
        if entry not in merged.entry_points:
            merged.entry_points.append(entry)
    for pattern in getattr(cli_args, "exclude", None) or []:
        if pattern not in merged.ignore_paths:
            merged.ignore_paths.append(pattern)
    if getattr(cli_args, "include_potentially", False):
        merged.thresholds.fail_on_potentially = True
    if getattr(cli_args, "no_fail", False):
        merged.thresholds = Thresholds(fail_on_reachable=False, fail_on_potentially=False)
    logger.debug("Effective config for %s: %r", project_root, merged)
    return merged
