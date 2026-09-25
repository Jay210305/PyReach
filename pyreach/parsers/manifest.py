"""Manifest parsing data contract and parser protocol.

:class:`Dependency` is the stable data contract consumed by every manifest
parser (requirements.txt, Pipfile.lock) and by the OSV mapper. The
:class:`ManifestParser` protocol is the interface every manifest parser must
implement so the CLI can auto-select a parser by filename without hard-coded
logic.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from packaging.requirements import InvalidRequirement, Requirement

from pyreach.exceptions import ConfigError, ParseError

SOURCE_REQUIREMENTS_TXT = "requirements.txt"
SOURCE_PIPFILE_LOCK = "Pipfile.lock"
VALID_SOURCES = frozenset({SOURCE_REQUIREMENTS_TXT, SOURCE_PIPFILE_LOCK})


def normalize_name(name: str) -> str:
    """Return the PEP 503 normalized form of *name*.

    Lowercases the name and collapses runs of ``-``, ``_`` and ``.`` into a
    single ``-`` (``Foo_Bar.Baz`` -> ``foo-bar-baz``).
    """
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class Dependency:
    """A single resolved dependency parsed from a manifest.

    ``name`` MUST be PEP 503 normalized (see :func:`normalize_name`). For exact
    pins ``version`` keeps the literal (``"2.31.0"``); for version ranges it
    stores the resolved lower bound with the comparison operator stripped
    (``">=2.0.0"`` -> ``"2.0.0"``). ``source`` is one of
    :data:`SOURCE_REQUIREMENTS_TXT` or :data:`SOURCE_PIPFILE_LOCK`.
    """

    name: str
    version: str
    source: str
    extra: str | None = None
    marker: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ParseError(f"dependency name must be non-empty, got {self.name!r}")
        if self.source not in VALID_SOURCES:
            raise ParseError(
                f"unknown dependency source {self.source!r}; "
                f"expected one of {sorted(VALID_SOURCES)}"
            )


#: Parsers return a plain list of dependencies. The alias keeps future typing
#: migrations cheap without changing the runtime contract.
ParserResult = list[Dependency]


@runtime_checkable
class ManifestParser(Protocol):
    """Interface every manifest parser must implement.

    ``supports()`` lets the CLI auto-select a parser by filename.
    ``parse()`` raises :class:`~pyreach.exceptions.ConfigError` when the file
    is missing and :class:`~pyreach.exceptions.ParseError` when it is malformed.
    ``parse()`` never executes the file (no ``eval``, no ``pip``); it only
    reads and parses text.
    """

    source_name: str = ""

    def supports(self, path: Path) -> bool: ...

    def parse(self, path: Path) -> list[Dependency]: ...


def _extract_version(req: Requirement) -> str:
    """Extract pinned version or lower bound from a Requirement specifier."""
    for spec in req.specifier:
        if spec.operator == "==":
            return spec.version
    for spec in req.specifier:
        if spec.operator in {">=", "~="}:
            return spec.version
    return ""


def _extract_extras(req: Requirement, raw_line: str) -> str | None:
    """Extract extras preserving original order when possible."""
    if not req.extras:
        return None
    match = re.search(r"\[(.*?)\]", raw_line)
    if match:
        raw_list = [e.strip() for e in match.group(1).split(",") if e.strip() in req.extras]
        if raw_list:
            return ",".join(raw_list)
    return ",".join(sorted(req.extras))


def _parse_non_pypi(line: str) -> tuple[str, str] | None:
    """Extract (name, version) from an editable install, direct URL, or local path."""
    line = re.sub(r"^(-e|--editable)\s+", "", line).strip()
    egg_match = re.search(r"#egg=([a-zA-Z0-9_.-]+)", line)
    if egg_match:
        return normalize_name(egg_match.group(1)), ""

    clean_line = line.split("?")[0].split("#")[0].strip()
    clean_path = Path(clean_line)
    filename = clean_path.name

    if filename.endswith(".whl"):
        parts = filename[:-4].split("-")
        if len(parts) >= 2:
            return normalize_name(parts[0]), parts[1]
        if parts:
            return normalize_name(parts[0]), ""

    archive_base = re.sub(r"\.(tar\.(?:gz|bz2|xz)|tgz|zip)$", "", filename)
    if archive_base != filename:
        parts = archive_base.rsplit("-", 1)
        if len(parts) == 2 and parts[1]:
            return normalize_name(parts[0]), parts[1]
        return normalize_name(archive_base), ""

    # Local directory or relative/absolute path
    if clean_line.startswith((".", "/", "\\")) or ("/" in clean_line or "\\" in clean_line):
        if filename and re.match(r"^[a-zA-Z0-9_.-]+$", filename):
            return normalize_name(filename), ""

    return None


class RequirementsTxtParser:
    """Parser for requirements.txt manifest files."""

    source_name: str = SOURCE_REQUIREMENTS_TXT

    def __init__(self, include_non_pypi: bool = False) -> None:
        self.include_non_pypi = include_non_pypi

    def supports(self, path: Path) -> bool:
        """Return True if path represents a requirements.txt file."""
        return path.name == SOURCE_REQUIREMENTS_TXT

    def parse(self, path: Path) -> list[Dependency]:
        """Parse requirements.txt into a list of normalized Dependency objects.

        Raises:
            ConfigError: If the file does not exist.
            ParseError: If a requirement line is malformed.
        """
        if not path.is_file():
            raise ConfigError(f"Manifest file not found: {path}")

        content = path.read_text(encoding="utf-8-sig")
        logical_lines = self._join_logical_lines(content.splitlines())
        dependencies: dict[str, Dependency] = {}

        for line in logical_lines:
            line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
            if not line or line.startswith("#"):
                continue

            line = re.sub(r"--hash=\S+", "", line).strip()
            if not line:
                continue

            first_token = line.split(maxsplit=1)[0]
            if first_token in {"-c", "-f", "-i", "-r"} or any(
                first_token == opt or first_token.startswith(f"{opt}=")
                for opt in (
                    "--index-url",
                    "--extra-index-url",
                    "--find-links",
                    "--trusted-host",
                    "--no-index",
                    "--prefer-binary",
                    "--no-binary",
                    "--only-binary",
                    "--constraint",
                    "--requirement",
                )
            ):
                continue

            if first_token in {"-e", "--editable"} or line.startswith(("-e ", "--editable ")):
                if self.include_non_pypi:
                    parsed = _parse_non_pypi(line)
                    if parsed:
                        name, ver = parsed
                        dependencies[name] = Dependency(
                            name=name,
                            version=ver,
                            source=SOURCE_REQUIREMENTS_TXT,
                        )
                continue

            if line.startswith(("http://", "https://", "ftp://", "git+", "hg+", "svn+", "bzr+")):
                if self.include_non_pypi:
                    parsed = _parse_non_pypi(line)
                    if parsed:
                        name, ver = parsed
                        dependencies[name] = Dependency(
                            name=name,
                            version=ver,
                            source=SOURCE_REQUIREMENTS_TXT,
                        )
                continue

            try:
                req = Requirement(line)
            except InvalidRequirement as exc:
                parsed = _parse_non_pypi(line)
                if parsed:
                    if self.include_non_pypi:
                        name, ver = parsed
                        dependencies[name] = Dependency(
                            name=name,
                            version=ver,
                            source=SOURCE_REQUIREMENTS_TXT,
                        )
                    continue
                raise ParseError(f"Malformed requirement in {path}: {line!r}") from exc

            name = normalize_name(req.name)
            dep = Dependency(
                name=name,
                version=_extract_version(req),
                source=SOURCE_REQUIREMENTS_TXT,
                extra=_extract_extras(req, line),
                marker=str(req.marker) if req.marker else None,
            )
            dependencies[name] = dep

        return list(dependencies.values())

    @staticmethod
    def _join_logical_lines(raw_lines: list[str]) -> list[str]:
        """Join physical lines using backslash line continuation."""
        logical_lines: list[str] = []
        current_line = ""

        for raw in raw_lines:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.endswith("\\"):
                part = stripped[:-1].strip()
                current_line = f"{current_line} {part}" if current_line else part
            else:
                current_line = f"{current_line} {stripped}" if current_line else stripped
                logical_lines.append(current_line)
                current_line = ""

        if current_line:
            logical_lines.append(current_line)

        return logical_lines


class PipfileLockParser:
    """Parser for Pipfile.lock manifest files.

    [NEGOTIABLE] Designated scope-cut candidate if schedule slips.
    """

    source_name: str = SOURCE_PIPFILE_LOCK

    def __init__(self, include_dev: bool = False, include_non_pypi: bool = False) -> None:
        self.include_dev = include_dev
        self.include_non_pypi = include_non_pypi

    def supports(self, path: Path) -> bool:
        """Return True if path represents a Pipfile.lock file."""
        return path.name == SOURCE_PIPFILE_LOCK

    def parse(self, path: Path) -> list[Dependency]:
        """Parse Pipfile.lock into a list of normalized Dependency objects.

        Raises:
            ConfigError: If the file does not exist.
            ParseError: If the file is not valid JSON or is malformed.
        """
        if not path.is_file():
            raise ConfigError(f"Manifest file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ParseError(f"Expected JSON object in {path}, got {type(data).__name__}")

        sections: list[dict[str, object]] = []
        default_section = data.get("default")
        if isinstance(default_section, dict):
            sections.append(default_section)
        if self.include_dev:
            develop_section = data.get("develop")
            if isinstance(develop_section, dict):
                sections.append(develop_section)

        dependencies: dict[str, Dependency] = {}

        for section in sections:
            for pkg_name in sorted(section.keys()):
                meta = section[pkg_name]
                if not isinstance(meta, dict):
                    continue

                is_non_pypi = any(k in meta for k in ("path", "git", "file", "url", "hg", "svn"))
                if is_non_pypi and not self.include_non_pypi:
                    continue

                name = normalize_name(pkg_name)
                raw_version = str(meta.get("version", ""))
                version = re.sub(r"^[=><~^!]+", "", raw_version).strip()
                extras_val = meta.get("extras")
                extra = (
                    ",".join(extras_val) if isinstance(extras_val, list) and extras_val else None
                )
                markers_val = meta.get("markers")
                marker = str(markers_val) if markers_val else None

                dep = Dependency(
                    name=name,
                    version=version,
                    source=SOURCE_PIPFILE_LOCK,
                    extra=extra,
                    marker=marker,
                )
                dependencies[name] = dep

        return list(dependencies.values())


def select_manifest_parser(project_root: Path) -> ManifestParser | None:
    """Select the appropriate manifest parser for a project root directory.

    Prefers requirements.txt, falls back to Pipfile.lock, or returns None.
    """
    req_path = project_root / SOURCE_REQUIREMENTS_TXT
    if req_path.is_file():
        return RequirementsTxtParser()
    pip_path = project_root / SOURCE_PIPFILE_LOCK
    if pip_path.is_file():
        return PipfileLockParser()
    return None
