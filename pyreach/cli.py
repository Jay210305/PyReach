"""Offline CLI orchestration; source and dependency code are parsed, never executed."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

import networkx as nx
from packaging.requirements import InvalidRequirement, Requirement

from pyreach import __version__
from pyreach.ast.builder import ASTBuilder, ModuleAST
from pyreach.ast.resolver import ModuleIndex
from pyreach.ast.symbols import SymbolTableBuilder
from pyreach.callgraph.engine import CallGraphEngine
from pyreach.config import PyReachConfig, resolve_config
from pyreach.exceptions import AnalysisError, ConfigError, OSVError, PyReachError
from pyreach.loaders.packages import PackageResolver, detect_site_packages
from pyreach.loaders.source import SourceLoader
from pyreach.osv.importer import sync_osv
from pyreach.osv.mapper import Vulnerability, VulnerabilityMapper
from pyreach.output.sarif import SarifBuilder, write_report
from pyreach.output.summary import summarize, text_summary
from pyreach.parsers.manifest import (
    Dependency,
    PipfileLockParser,
    RequirementsTxtParser,
    normalize_name,
)
from pyreach.reachability.analyzer import analyze_reachability, imported_packages
from pyreach.reachability.entrypoints import detect_or_fail


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pyreach",
        description="Local static vulnerability reachability analysis",
        epilog=(
            "Examples: pyreach ./project -d osv.db -f text; "
            "pyreach sync-osv --source advisories.jsonl"
        ),
    )
    p.add_argument("project_path", nargs="?", help="Python project root (or sync-osv)")
    p.add_argument("-m", "--manifest")
    p.add_argument("-d", "--db-path")
    p.add_argument("-o", "--output")
    p.add_argument("-e", "--entry-point", action="append", default=[])
    p.add_argument("-k", "--max-depth", type=int, help="Maximum call depth, 0..7 (default 5)")
    p.add_argument("--include-potentially", action="store_true")
    p.add_argument("--include-all", action="store_true")
    p.add_argument("--no-fail", action="store_true")
    p.add_argument("-f", "--format", choices=["sarif", "json", "text"], default="sarif")
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument(
        "--cache",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse a content-addressed graph in the user's cache directory",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("--version", action="version", version=f"PyReach {__version__}")
    return p


def _confined(path: str, root: Path) -> Path:
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ConfigError(f"Path must be inside project root: {path}")
    return resolved


def _dependencies(root: Path, config: PyReachConfig, paths: list[Path]) -> list[Dependency]:
    import importlib.metadata

    manifest = _confined(config.manifest, root)
    if not manifest.is_file():
        raise ConfigError(f"Missing manifest: {manifest}")
    reader = PipfileLockParser() if manifest.name == "Pipfile.lock" else RequirementsTxtParser()
    dependencies = reader.parse(manifest)
    distributions = {
        normalize_name(d.metadata["Name"]): d
        for d in importlib.metadata.distributions(path=[str(p) for p in paths])
        if d.metadata["Name"]
    }
    seen: dict[str, Dependency] = {}
    queue = list(dependencies)
    while queue:
        dep = queue.pop(0)
        if dep.name in seen:
            continue
        distribution = distributions.get(dep.name)
        version = distribution.version if distribution else dep.version
        seen[dep.name] = Dependency(dep.name, version, dep.source, dep.extra, dep.marker)
        if distribution:
            for raw in distribution.requires or []:
                try:
                    requirement = Requirement(raw)
                    if requirement.marker and not requirement.marker.evaluate():
                        continue
                    name = normalize_name(requirement.name)
                    resolved = distributions.get(name)
                    if name not in seen:
                        queue.append(
                            Dependency(
                                name, resolved.version if resolved else "unknown", dep.source
                            )
                        )
                except InvalidRequirement as exc:
                    raise ConfigError(f"Invalid dependency metadata: {raw}") from exc
    return list(seen.values())


def _modules(
    root: Path, config: PyReachConfig, dependencies: list[Dependency], paths: list[Path]
) -> tuple[list[ModuleAST], list[ModuleAST], list[str]]:
    sources = SourceLoader(root, config.ignore_paths).discover()
    application = ASTBuilder(root).build_all(sources)
    diagnostics = []
    if len(application) != len(sources):
        diagnostics.append(
            f"Partial source analysis: {len(sources) - len(application)} file(s) "
            "unreadable or invalid"
        )
    modules = list(application)
    resolver = PackageResolver(search_paths=paths)
    known = {m.module_fqn for m in modules}
    for package in resolver.resolve_all(dependencies).values():
        builder = ASTBuilder(package.location, package.location)
        for name in package.top_level:
            start = package.location / name
            files = sorted(start.rglob("*.py")) if start.is_dir() else [start.with_suffix(".py")]
            for file in files:
                if not file.is_file():
                    continue
                mod = builder.build_file(file)
                if mod is None:
                    diagnostics.append(f"Partial dependency source: {file.name}")
                elif mod.module_fqn not in known:
                    known.add(mod.module_fqn)
                    modules.append(mod)
    index = ModuleIndex(modules)
    for module in modules:
        SymbolTableBuilder(module, index.get).build()
    return application, modules, diagnostics


def _graph(modules: list[ModuleAST], use_cache: bool) -> nx.DiGraph:
    digest = hashlib.sha256(f"{__version__}:graph-v2".encode())
    for module in modules:
        digest.update(module.file_path.encode())
        digest.update(Path(module.file_path).read_bytes())
    cache = Path.home() / ".cache/pyreach" / f"{digest.hexdigest()}.json"
    if use_cache:
        try:
            data = json.loads(cache.read_text())
            return nx.node_link_graph(data, edges="edges", directed=True, multigraph=False)
        except (OSError, ValueError, KeyError, TypeError, nx.NetworkXError):
            pass
    try:
        graph = CallGraphEngine(ModuleIndex(modules)).build(modules)
    except nx.NetworkXException as exc:
        raise AnalysisError(f"Call graph construction failed: {exc}") from exc
    if use_cache:
        serializable = graph.copy()
        for _, attrs in serializable.nodes(data=True):
            attrs.pop("node", None)
        try:
            write_report(cache, nx.node_link_data(serializable, edges="edges"))
        except PyReachError:
            logging.getLogger(__name__).warning(
                "Graph cache unavailable; scan completed without persistence"
            )
    return graph


def run_scan(args: argparse.Namespace) -> int:
    root = Path(args.project_path).expanduser().resolve()
    if not root.is_dir():
        raise ConfigError(f"Project root does not exist: {root}")
    config = resolve_config(args, root)
    db = Path(config.osv_db).expanduser().resolve()
    if not db.is_file():
        raise OSVError(
            f"Missing local OSV database: {db}. Run pyreach sync-osv --source FILE first."
        )
    paths = detect_site_packages(root)
    dependencies = _dependencies(root, config, paths)
    vulnerabilities: list[Vulnerability] = []
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        mapper = VulnerabilityMapper(conn)
        for dependency in dependencies:
            vulnerabilities.extend(
                mapper.find_by_package_and_version(dependency.name, dependency.version)
            )
    application, modules, diagnostics = _modules(root, config, dependencies, paths)
    graph = _graph(modules, args.cache)
    module_entries = [
        f"{m.module_fqn}.__main__" for m in application if f"{m.module_fqn}.__main__" in graph
    ]
    entries = detect_or_fail(
        application, overrides=[*config.entry_points, *module_entries], known_fqns=set(graph)
    )
    if any(entry.replace(":", ".") not in graph for entry in config.entry_points):
        raise ConfigError("Entry point not found in parsed sources; verify -e module:function")
    entries = [entry for entry in entries if entry in graph]
    if not entries:
        raise ConfigError("No executable entry points; specify -e module:function")
    imports = imported_packages(application)
    imports.update(normalize_name(x) for x in list(imports))
    for vuln in vulnerabilities:
        if any(symbol.split(".")[0] in imports for symbol in vuln.affected_symbols):
            imports.add(vuln.package_name)
    results = analyze_reachability(graph, entries, vulnerabilities, config.max_depth, imports)
    if diagnostics:
        for result in results.values():
            if result.status == "NOT_REACHABLE":
                result.status = "POTENTIALLY_REACHABLE"
                result.reasoning = "Partial source analysis; reachability cannot be ruled out."
    document = summarize(results)
    document["diagnostics"] = diagnostics
    document["configuration"] = {
        "max_depth": config.max_depth,
        "entry_points": entries,
        "offline": True,
    }
    versions = {d.name: d.version for d in dependencies}
    if args.format == "sarif":
        builder = SarifBuilder(__version__, root, graph)
        for (_, symbol), result in results.items():
            builder.add_result(
                result,
                include_not_reachable=args.include_all,
                symbol=symbol,
                installed_version=versions.get(result.vulnerability.package_name, "unknown"),
            )
        output: Any = builder.build()
        output["runs"][0]["properties"] = {
            "summary": document["summary"],
            "diagnostics": diagnostics,
        }
    elif args.format == "json":
        output = document
    else:
        output = text_summary(document)
        if not args.quiet:
            print(output)
    destination = (
        Path(args.output).expanduser() if args.output else root / f"pyreach-results.{args.format}"
    )
    if not destination.is_absolute():
        destination = root / destination
    protected = {
        _confined(config.manifest, root),
        db,
        root / ".pyreach.yml",
        root / ".pyreach.yaml",
    }
    if destination.resolve() in protected or destination.suffix == ".py":
        raise ConfigError(
            "Report destination must not overwrite source, configuration, manifest or database"
        )
    write_report(destination, output)
    blocked = any(
        (r.status == "REACHABLE" and config.thresholds.fail_on_reachable)
        or (r.status == "POTENTIALLY_REACHABLE" and config.thresholds.fail_on_potentially)
        for r in results.values()
    )
    return int(blocked)


def _sync(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="pyreach sync-osv", description="Prepare the local database from offline JSON/JSONL"
    )
    p.add_argument("--source", required=True)
    p.add_argument("-d", "--db-path", default="~/.pyreach/osv.db")
    p.add_argument("--incremental", action="store_true")
    args = p.parse_args(argv)
    stats = sync_osv(Path(args.db_path).expanduser(), args.source, args.incremental)
    from dataclasses import asdict

    print(json.dumps(asdict(stats), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    verbose = "--verbose" in arguments or "-v" in arguments
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="[%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    try:
        if arguments and arguments[0] == "sync-osv":
            return _sync(arguments[1:])
        args = parser().parse_args(arguments)
        if not args.project_path:
            raise ConfigError("PROJECT_PATH is required; use --help")
        if not args.quiet and sys.stderr.isatty():
            print(
                "[INFO] Reading local data, parsing AST and analyzing reachability...",
                file=sys.stderr,
            )
        return run_scan(args)
    except (PyReachError, OSError, UnicodeError, sqlite3.Error, ValueError, MemoryError) as exc:
        logging.getLogger(__name__).error("%s", exc, exc_info=verbose)
        return 2
