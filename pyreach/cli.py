"""PyReach command-line interface (S4-T3).

Wires manifest parsing, OSV lookup, AST loading, call-graph construction,
reachability analysis and SARIF/JSON/text output into a single command.
Uses only :mod:`argparse` (stdlib); no Click/Typer dependency.
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import traceback
from enum import IntEnum
from importlib import metadata
from pathlib import Path

import networkx as nx

from pyreach import __version__
from pyreach.ast.builder import ASTBuilder, ModuleAST
from pyreach.ast.resolver import ModuleIndex
from pyreach.ast.symbols import SymbolTableBuilder
from pyreach.callgraph.engine import CallGraphEngine
from pyreach.config import MAX_SCAN_DEPTH, resolve_config
from pyreach.db.connection import get_db_connection
from pyreach.exceptions import ConfigError, OSVError, PyReachError
from pyreach.loaders.packages import InstalledPackage, PackageResolver, detect_site_packages
from pyreach.loaders.source import SourceLoader
from pyreach.osv.importer import sync_osv
from pyreach.osv.mapper import Vulnerability, VulnerabilityMapper
from pyreach.output.sarif import SarifBuilder
from pyreach.parsers.manifest import (
    Dependency,
    PipfileLockParser,
    RequirementsTxtParser,
    normalize_name,
    select_manifest_parser,
)
from pyreach.reachability.analyzer import analyze_reachability, imported_packages
from pyreach.reachability.contracts import ReachabilityResult
from pyreach.reachability.entrypoints import detect_or_fail

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST = "requirements.txt"
DEFAULT_PIPFILE_LOCK = "Pipfile.lock"
DEFAULT_DB_PATH = "~/.pyreach/osv.db"
DEFAULT_SARIF_OUTPUT = "pyreach-results.sarif"
DEFAULT_JSON_OUTPUT = "pyreach-results.json"
DEFAULT_MAX_DEPTH = 5
DEFAULT_OSV_SOURCE = "https://storage.googleapis.com/osv-vulnerabilities/PyPI/all.zip"


class ExitCode(IntEnum):
    """Process exit codes (S4-T4 rules, implemented here for the orchestrator)."""

    SUCCESS = 0
    FINDINGS = 1
    ERROR = 2


def _tool_version() -> str:
    try:
        return metadata.version("pyreach")
    except metadata.PackageNotFoundError:
        return __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the ``pyreach`` argument parser (spec §4, all options)."""
    parser = argparse.ArgumentParser(
        prog="pyreach",
        description="Static reachability analysis for Python dependency vulnerabilities.",
        epilog=(
            "examples:\n"
            "  pyreach /path/to/project\n"
            "  pyreach /path/to/project -e main.app -e api.routes.health_check -o results.sarif\n"
            "  pyreach /path/to/project -f text --verbose\n"
            "  pyreach /path/to/project --include-potentially -o sarif/output.sarif\n"
            "  pyreach sync-osv --source /path/to/PyPI/all.zip\n"
            "\nexit codes: 0 clean (or --no-fail), 1 reachable findings,\n"
            "2 configuration/runtime error."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_path",
        metavar="PROJECT_PATH",
        nargs="?",
        default=None,
        help="Root directory of the Python project to analyze.",
    )
    parser.add_argument(
        "-m",
        "--manifest",
        default=None,
        help=f"Dependency manifest (default: {DEFAULT_MANIFEST}; "
        f"falls back to {DEFAULT_PIPFILE_LOCK} when present).",
    )
    parser.add_argument(
        "-d",
        "--db-path",
        default=None,
        help=f"Path to the local OSV SQLite database (default: {DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file path (default: pyreach-results.sarif for sarif, "
        "pyreach-results.json for json; text prints to stdout unless -o is given).",
    )
    parser.add_argument(
        "-e",
        "--entry-point",
        action="append",
        default=None,
        help="Additional entry point function FQN (repeatable; merged with auto-detected).",
    )
    parser.add_argument(
        "-k",
        "--max-depth",
        type=int,
        default=None,
        help=f"Maximum call graph traversal depth, 0-{MAX_SCAN_DEPTH} (default: 5).",
    )
    parser.add_argument(
        "--include-potentially",
        action="store_true",
        help="Treat POTENTIALLY_REACHABLE as a failure (exit 1).",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include NOT_REACHABLE results in the output.",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Always exit 0 regardless of findings (errors still exit 2).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("sarif", "json", "text"),
        default="sarif",
        help="Output format (default: sarif).",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        help="Path pattern to exclude from analysis (repeatable, e.g. tests/).",
    )
    parser.add_argument(
        "--cache",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse the call graph cache when available (default: on; in-memory build).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress non-error output (CI mode)."
    )
    parser.add_argument("--version", action="version", version=f"PyReach {_tool_version()}")
    return parser


parser = build_parser


def build_sync_parser() -> argparse.ArgumentParser:
    """Build the offline-database refresh command parser."""
    parser = argparse.ArgumentParser(prog="pyreach sync-osv")
    parser.add_argument("-d", "--db-path", default=DEFAULT_DB_PATH)
    parser.add_argument("--source", default=DEFAULT_OSV_SOURCE)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser


def _resolve_project(project_arg: str | None) -> Path:
    if not project_arg:
        raise ConfigError("Missing PROJECT_PATH. Usage: pyreach [OPTIONS] <PROJECT_PATH>")
    project = Path(project_arg).resolve()
    if not project.is_dir():
        raise ConfigError(f"Project path is not a directory: {project}")
    return project


def parse_manifest(manifest_arg: str | None, project: Path) -> list[Dependency]:
    """Parse the project manifest into dependencies.

    Raises:
        ConfigError: Manifest missing or filename unsupported.
        ParseError: Manifest malformed (propagated from the parser).
    """
    if manifest_arg:
        candidate = Path(manifest_arg)
        manifest_path = candidate if candidate.is_absolute() else project / candidate
    else:
        default_txt = project / DEFAULT_MANIFEST
        default_lock = project / DEFAULT_PIPFILE_LOCK
        if default_txt.is_file():
            manifest_path = default_txt
        elif default_lock.is_file():
            manifest_path = default_lock
        else:
            manifest_path = default_txt
    manifest_path = manifest_path.resolve()
    try:
        manifest_path.relative_to(project.resolve())
    except ValueError as exc:
        raise ConfigError(f"Manifest path is outside project: {manifest_path}") from exc
    if not manifest_path.is_file():
        raise ConfigError(
            f"Manifest file '{manifest_path.name}' not found in {project}. "
            "Use --manifest to specify location."
        )
    for parser in (RequirementsTxtParser(), PipfileLockParser()):
        if parser.supports(manifest_path):
            return parser.parse(manifest_path)
    # An explicitly-requested manifest that no parser supports is an error,
    # not a signal to silently scan a different file (security gate).
    if manifest_arg:
        raise ConfigError(
            f"Unsupported manifest '{manifest_path.name}'; "
            "expected requirements.txt or Pipfile.lock."
        )
    auto = select_manifest_parser(project)
    if auto is not None:
        for path in project.iterdir():
            if path.is_file() and auto.supports(path):
                return auto.parse(path)
    raise ConfigError(
        f"Unsupported manifest '{manifest_path.name}'; expected requirements.txt or Pipfile.lock."
    )


def load_vulnerabilities(
    db_path_arg: str | None, dependencies: list[Dependency]
) -> tuple[list[Vulnerability], dict[str, str]]:
    """Look up advisories affecting the installed dependencies.

    Raises:
        OSVError: Database file missing or unreadable.
    """
    db_path = Path(db_path_arg).expanduser() if db_path_arg else Path(DEFAULT_DB_PATH).expanduser()
    if not db_path.exists():
        raise OSVError(f"OSV database not found at {db_path}. Run 'pyreach sync-osv' to download.")
    versions = {dep.name: dep.version for dep in dependencies}
    vulnerabilities: list[Vulnerability] = []
    try:
        with get_db_connection(db_path) as conn:
            mapper = VulnerabilityMapper(conn)
            for dep in dependencies:
                vulnerabilities.extend(mapper.find_by_package_and_version(dep.name, dep.version))
    except sqlite3.Error as exc:
        raise OSVError(
            f"OSV database at {db_path} is corrupt or missing advisory tables. "
            "Run 'pyreach sync-osv' to rebuild it."
        ) from exc
    return vulnerabilities, versions


def discover_modules(project: Path, excludes: list[str]) -> tuple[list[ModuleAST], list[str]]:
    """Discover and parse application sources (skips unreadable files with warnings)."""
    loader = SourceLoader(project, ignore_patterns=excludes)
    builder = ASTBuilder(module_root=project)
    modules: list[ModuleAST] = []
    diagnostics: list[str] = []
    for sf in loader.discover():
        try:
            m = builder.build_file(sf.path)
            if m is not None:
                modules.append(m)
            else:
                diagnostics.append(f"Failed to parse source: {sf.path}")
        except Exception as exc:
            diagnostics.append(f"Failed to parse {sf.path}: {exc}")
    return modules, diagnostics


def _expand_transitive_dependencies(
    dependencies: list[Dependency], search_paths: list[Path]
) -> list[Dependency]:
    import importlib.metadata

    from packaging.requirements import InvalidRequirement, Requirement

    distributions = {
        normalize_name(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(p) for p in search_paths])
        if "Name" in d.metadata and d.metadata["Name"]
    }
    seen: dict[str, Dependency] = {}
    queue = list(dependencies)
    while queue:
        dep = queue.pop(0)
        norm = normalize_name(dep.name)
        if norm in seen:
            continue
        distribution = distributions.get(norm)
        version = distribution.version if distribution else dep.version
        dep_obj = Dependency(dep.name, version, dep.source, dep.extra, dep.marker)
        seen[norm] = dep_obj
        if distribution:
            for raw in distribution.requires or []:
                try:
                    requirement = Requirement(raw)
                    if requirement.marker and not requirement.marker.evaluate():
                        continue
                    req_name = normalize_name(requirement.name)
                    if req_name not in seen:
                        resolved = distributions.get(req_name)
                        queue.append(
                            Dependency(
                                requirement.name,
                                resolved.version if resolved else "unknown",
                                dep.source,
                            )
                        )
                except InvalidRequirement:
                    continue
    return list(seen.values())


def _symbol_module_file(symbol: str, pkg: InstalledPackage) -> Path | None:
    parts = symbol.split(".")
    if not parts or any(part == ".." or part == "" for part in parts):
        return None
    base = pkg.location.resolve()
    for i in range(len(parts) - 1, 0, -1):
        rel = Path(*parts[:i])
        for candidate in (
            base / rel.with_suffix(".py"),
            base / rel / "__init__.py",
        ):
            try:
                resolved = candidate.resolve()
                resolved.relative_to(base)
            except ValueError:
                continue
            if resolved.is_file():
                return resolved
    return None


def load_library_modules(
    vulnerabilities: list[Vulnerability], resolver: PackageResolver
) -> list[ModuleAST]:
    """Parse the defining modules of vulnerable symbols (best-effort, never aborts)."""
    builders: dict[Path, ASTBuilder] = {}
    modules: list[ModuleAST] = []
    seen: set[Path] = set()
    for vuln in vulnerabilities:
        try:
            pkg = resolver.resolve(vuln.package_name)
        except Exception as exc:
            logger.warning("Skipping installed-package lookup for %s: %s", vuln.package_name, exc)
            continue
        if pkg is None:
            continue
        for symbol in vuln.affected_symbols:
            try:
                target = _symbol_module_file(symbol, pkg)
            except Exception as exc:
                logger.warning("Skipping library module lookup for %s: %s", symbol, exc)
                continue
            if target is None or target in seen:
                continue
            seen.add(target)
            try:
                builder = builders.get(pkg.location)
                if builder is None:
                    builder = ASTBuilder(module_root=pkg.location)
                    builders[pkg.location] = builder
                module = builder.build_file(target)
            except Exception as exc:
                logger.warning("Skipping library module %s: %s", target, exc)
                continue
            if module is not None:
                modules.append(module)
    return modules


def combine_modules(app_modules: list[ModuleAST], lib_modules: list[ModuleAST]) -> list[ModuleAST]:
    """Merge app and library modules; app definitions win on FQN collisions."""
    merged = {mod.module_fqn: mod for mod in lib_modules}
    merged.update({mod.module_fqn: mod for mod in app_modules})
    return list(merged.values())


def build_call_graph(modules: list[ModuleAST]) -> nx.DiGraph:
    """Build the NetworkX DiGraph from parsed modules."""
    index = ModuleIndex(modules)
    for mod in modules:
        SymbolTableBuilder(mod, index.get).build()
    return CallGraphEngine(index).build(modules)


def resolve_entry_points_cli(
    app_modules: list[ModuleAST], cli_entries: list[str], graph: nx.DiGraph
) -> list[str]:
    """Detect entry points, merge CLI overrides, fail when empty."""
    return detect_or_fail(app_modules, list(cli_entries), known_fqns=set(graph.nodes))


def compute_exit_code(results: list[ReachabilityResult], args: argparse.Namespace) -> ExitCode:
    """Map findings and flags to the CI gate exit code (S4-T4 rules).

    ``fail_on_reachable`` comes from ``thresholds`` in ``.pyreach.yml`` (S4-T5);
    it defaults to ``True`` when the attribute is absent.
    """
    if args.no_fail:
        return ExitCode.SUCCESS
    statuses = {result.status for result in results}
    if "REACHABLE" in statuses and getattr(args, "fail_on_reachable", True):
        return ExitCode.FINDINGS
    if "POTENTIALLY_REACHABLE" in statuses and args.include_potentially:
        return ExitCode.FINDINGS
    return ExitCode.SUCCESS


def _symbol_file_line(
    graph: nx.DiGraph, project: Path, symbol: str
) -> tuple[str | None, int | None]:
    if symbol not in graph:
        return None, None
    data = graph.nodes[symbol]
    raw_file = data.get("file_path")
    line = data.get("line_number")
    if raw_file is None:
        return None, line if isinstance(line, int) else None
    try:
        rel = Path(str(raw_file)).resolve().relative_to(project.resolve())
        return rel.as_posix(), line if isinstance(line, int) else None
    except ValueError:
        return str(raw_file).replace("\\", "/"), line if isinstance(line, int) else None


def _count_by_status(results: list[ReachabilityResult]) -> dict[str, int]:
    counts = {"REACHABLE": 0, "POTENTIALLY_REACHABLE": 0, "NOT_REACHABLE": 0}
    for result in results:
        counts[result.status] += 1
    return counts


def format_text(
    project: Path,
    entries: list[str],
    max_depth: int,
    results: list[ReachabilityResult],
    graph: nx.DiGraph,
    versions: dict[str, str],
) -> str:
    """Render the human-readable summary (spec §2.4, ASCII only)."""
    counts = _count_by_status(results)
    lines = [
        f"PyReach {_tool_version()} - Static Reachability Analysis",
        "=============================================",
        f"Project: {project}",
        f"Entry points: {', '.join(entries) if entries else '(none)'}",
        f"Max depth: {max_depth}",
        "",
        "Results Summary:",
        "----------------",
        f"REACHABLE:              {counts['REACHABLE']}",
        f"POTENTIALLY REACHABLE:  {counts['POTENTIALLY_REACHABLE']}",
        f"NOT REACHABLE:          {counts['NOT_REACHABLE']}",
        f"TOTAL:                  {len(results)}",
        "",
    ]
    ordered = sorted(results, key=lambda r: (r.status, r.vulnerability.package_name))

    def _emit(section: str, group: list[ReachabilityResult]) -> None:
        if not group:
            return
        lines.append(section)
        for result in group:
            vuln = result.vulnerability
            cve = vuln.cve_id or vuln.osv_id
            version = versions.get(normalize_name(vuln.package_name), "")
            pkg_part = f"{vuln.package_name}=={version}" if version else vuln.package_name
            severity = vuln.severity_level or "UNKNOWN"
            symbol = result.paths[0][-1] if result.paths and result.paths[0] else "?"
            lines.append(f"  - {cve} ({severity}) in {pkg_part}")
            if result.paths and result.paths[0]:
                lines.append(f"    Path: {' -> '.join(result.paths[0])}")
            else:
                lines.append(f"    Reason: {' '.join(result.reasoning.split())}")
            file_path, line = _symbol_file_line(graph, project, symbol)
            if file_path is not None:
                lines.append(f"    File: {file_path}:{line if line is not None else '?'}")

    _emit("Reachable CVEs:", [r for r in ordered if r.status == "REACHABLE"])
    _emit(
        "Potentially reachable CVEs:",
        [r for r in ordered if r.status == "POTENTIALLY_REACHABLE"],
    )
    return "\n".join(lines) + "\n"


def build_json_document(
    project: Path,
    results: dict[tuple[str, str, str], ReachabilityResult],
    graph: nx.DiGraph,
    versions: dict[str, str],
    diagnostics: list[str] | None = None,
) -> dict[str, object]:
    """Render the non-SARIF machine-readable format (spec §2.4)."""
    counts = _count_by_status(list(results.values()))
    items = []
    for (_osv_id, _package, symbol), result in sorted(results.items()):
        vuln = result.vulnerability
        file_path, line = _symbol_file_line(graph, project, symbol)
        items.append(
            {
                "vulnerability": {
                    "osvId": vuln.osv_id,
                    "osv_id": vuln.osv_id,
                    "cveId": vuln.cve_id,
                    "cve_id": vuln.cve_id,
                    "packageName": vuln.package_name,
                    "package_name": vuln.package_name,
                    "installedVersion": versions.get(normalize_name(vuln.package_name), ""),
                    "installed_version": versions.get(normalize_name(vuln.package_name), ""),
                    "severity": vuln.severity_level,
                },
                "status": result.status,
                "path": list(result.paths[0]) if result.paths and result.paths[0] else [],
                "location": ({"file": file_path, "line": line} if file_path is not None else None),
            }
        )
    doc: dict[str, object] = {
        "tool": "PyReach",
        "version": _tool_version(),
        "project": str(project),
        "summary": {
            "total": len(items),
            "reachable": counts["REACHABLE"],
            "potentially_reachable": counts["POTENTIALLY_REACHABLE"],
            "not_reachable": counts["NOT_REACHABLE"],
        },
        "results": items,
    }
    if diagnostics is not None:
        doc["diagnostics"] = list(diagnostics)
    return doc


def emit_output(
    args: argparse.Namespace,
    project: Path,
    results: dict[tuple[str, str, str], ReachabilityResult],
    graph: nx.DiGraph,
    versions: dict[str, str],
    entries: list[str] | None = None,
    diagnostics: list[str] | None = None,
) -> Path | None:
    """Serialize results per --format; returns the written file, if any."""
    if args.format == "sarif":
        out = Path(args.output) if args.output else Path(DEFAULT_SARIF_OUTPUT)
        builder = SarifBuilder(_tool_version(), project, graph=graph, installed_versions=versions)
        for (_osv_id, _package, symbol), result in results.items():
            builder.add_result(result, include_not_reachable=args.include_all, symbol=symbol)
        doc = builder.build()
        if diagnostics:
            runs = doc.get("runs")
            if isinstance(runs, list) and runs:
                first_run = runs[0]
                if isinstance(first_run, dict):
                    props = first_run.setdefault("properties", {})
                    if isinstance(props, dict):
                        props["diagnostics"] = list(diagnostics)
        builder.write(out)
        return out
    if args.format == "json":
        out = Path(args.output) if args.output else Path(DEFAULT_JSON_OUTPUT)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            build_json_document(project, results, graph, versions, diagnostics), indent=2
        ) + "\n"
        out.write_text(payload, encoding="utf-8")
        return out
    report = format_text(
        project,
        list(entries or []),
        args.max_depth if args.max_depth is not None else DEFAULT_MAX_DEPTH,
        list(results.values()),
        graph,
        versions,
    )
    print(report, end="")
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        return out
    return None


def _progress(step: int, total: int, message: str, *, quiet: bool) -> None:
    if quiet or not sys.stderr.isatty():
        return
    print(f"[{step}/{total}] {message}...", file=sys.stderr)


def _configure_logging(args: argparse.Namespace) -> None:
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.ERROR
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, force=True)


def run_scan(args: argparse.Namespace) -> ExitCode:
    """Execute the full scan pipeline and return the CI gate exit code."""
    quiet = bool(args.quiet)
    project = _resolve_project(args.project_path)
    cfg = resolve_config(args, project)
    max_depth = cfg.max_depth
    if max_depth < 0 or max_depth > MAX_SCAN_DEPTH:
        raise ConfigError(f"max_depth must be in [0, {MAX_SCAN_DEPTH}], got {max_depth}")
    args.max_depth = max_depth
    args.include_potentially = args.include_potentially or cfg.thresholds.fail_on_potentially
    args.fail_on_reachable = cfg.thresholds.fail_on_reachable

    if args.manifest is not None or cfg.manifest != DEFAULT_MANIFEST:
        manifest_arg: str | None = cfg.manifest
    else:
        manifest_arg = None

    search_paths = detect_site_packages(project) or []
    _progress(1, 5, "Parsing manifest", quiet=quiet)
    dependencies = parse_manifest(manifest_arg, project)
    dependencies = _expand_transitive_dependencies(dependencies, search_paths)

    _progress(2, 5, "Loading advisories", quiet=quiet)
    vulnerabilities, versions = load_vulnerabilities(cfg.osv_db, dependencies)
    if not vulnerabilities:
        logger.info("No advisories match the installed dependencies; nothing to analyze.")
        emit_output(args, project, {}, nx.DiGraph(), versions, [])
        return ExitCode.SUCCESS

    _progress(3, 5, "Building call graph", quiet=quiet)
    app_modules, diagnostics = discover_modules(project, list(cfg.ignore_paths))
    resolver = PackageResolver(search_paths=search_paths or None)
    lib_modules = load_library_modules(vulnerabilities, resolver)
    import_names: dict[str, set[str]] = {}
    for vuln in vulnerabilities:
        pkg = resolver.resolve(vuln.package_name)
        if pkg is not None:
            import_names[pkg.name] = set(pkg.top_level)
    graph = build_call_graph(combine_modules(app_modules, lib_modules))
    if cfg.entry_points and any(entry.replace(":", ".") not in graph for entry in cfg.entry_points):
        raise ConfigError("Entry point not found in parsed sources; verify -e module:function")
    module_entries = [
        f"{m.module_fqn}.__main__" for m in app_modules if f"{m.module_fqn}.__main__" in graph
    ]
    entries = resolve_entry_points_cli(app_modules, [*cfg.entry_points, *module_entries], graph)

    _progress(4, 5, "Analyzing reachability", quiet=quiet)
    results = analyze_reachability(
        graph,
        entries,
        vulnerabilities,
        max_depth=max_depth,
        application_imports=imported_packages(app_modules),
        package_import_names=import_names,
    )
    if diagnostics:
        for result in results.values():
            if result.status == "NOT_REACHABLE":
                result.status = "POTENTIALLY_REACHABLE"
                result.reasoning = "Partial source analysis; reachability cannot be ruled out."

    _progress(5, 5, "Writing output", quiet=quiet)
    written = emit_output(args, project, results, graph, versions, entries, diagnostics)
    code = compute_exit_code(list(results.values()), args)
    if not quiet and args.format != "text":
        counts = _count_by_status(list(results.values()))
        target = f" -> {written}" if written is not None else ""
        print(
            f"Scan complete: {counts['REACHABLE']} reachable, "
            f"{counts['POTENTIALLY_REACHABLE']} potentially reachable, "
            f"{counts['NOT_REACHABLE']} not reachable{target}"
        )
    return code


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the scan, and return the exit code."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    syncing = bool(arguments and arguments[0] == "sync-osv")
    args = (
        build_sync_parser().parse_args(arguments[1:])
        if syncing
        else build_parser().parse_args(arguments)
    )
    _configure_logging(args)
    try:
        if syncing:
            stats = sync_osv(
                Path(args.db_path).expanduser(), args.source, incremental=args.incremental
            )
            if not args.quiet:
                print(f"OSV sync complete: {stats.imported} advisories imported.")
            return int(ExitCode.SUCCESS)
        return int(run_scan(args))
    except PyReachError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return int(ExitCode.ERROR)
    except KeyboardInterrupt:
        print("Error: interrupted.", file=sys.stderr)
        return int(ExitCode.ERROR)
    except MemoryError:
        print(
            "Error: Memory limit exceeded during call graph construction. "
            "Try reducing --max-depth or excluding large packages (--exclude).",
            file=sys.stderr,
        )
        return int(ExitCode.ERROR)
    except Exception as exc:
        if args.verbose:
            traceback.print_exc()
        print(f"Error: unexpected failure: {exc}", file=sys.stderr)
        return int(ExitCode.ERROR)


if __name__ == "__main__":
    raise SystemExit(main())
