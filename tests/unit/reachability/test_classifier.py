"""Tests for S3-T6 reachability classifier (pure decision logic)."""

import itertools

from pyreach.osv.mapper import Vulnerability
from pyreach.reachability.classifier import ReachabilityClassifier, SymbolContext
from pyreach.reachability.contracts import ReachabilityResult, TraversalOutcome


def _make_vuln(package: str = "pkg", symbols: tuple[str, ...] = ("pkg.func",)) -> Vulnerability:
    return Vulnerability(
        osv_id="TEST-1",
        cve_id=None,
        package_name=package,
        severity_score=None,
        severity_level=None,
        summary="test advisory",
        affected_symbols=list(symbols),
        version_introduced=None,
        version_fixed=None,
    )


def _ctx(**overrides) -> SymbolContext:
    defaults = dict(
        symbol_fqn="pkg.func",
        vulnerability=_make_vuln(),
        package_imported=False,
        exact_node_exists=True,
        dynamic_in_chain=False,
        unresolved_imports=False,
        max_depth_exceeded=False,
    )
    defaults.update(overrides)
    return SymbolContext(**defaults)


def _evidence(
    status: str = "NOT_REACHABLE",
    paths: list[list[str]] | None = None,
    encountered_dynamic: bool = False,
    depth_exceeded: bool = False,
) -> TraversalOutcome:
    return TraversalOutcome(status, paths or [], encountered_dynamic, depth_exceeded)


classifier = ReachabilityClassifier()


def test_static_path_is_reachable() -> None:
    evidence = _evidence("REACHABLE", [["main", "a", "pkg.func"]])
    result = classifier.classify(evidence, _ctx())
    assert result.status == "REACHABLE"
    assert result.paths == [["main", "a", "pkg.func"]]
    assert result.entry_points_reached == ["main"]
    assert result.reasoning == "Static call path found from main (depth 2)."


def test_no_path_no_dynamic() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=True, exact_node_exists=True))
    assert result.status == "NOT_REACHABLE"
    assert result.reasoning == "No call path found."


def test_dynamic_forces_potential() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=True, dynamic_in_chain=True))
    assert result.status == "POTENTIALLY_REACHABLE"
    assert "Dynamic" in result.reasoning


def test_package_not_imported() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=False, exact_node_exists=False))
    assert result.status == "NOT_REACHABLE"
    assert "package not imported" in result.reasoning


def test_package_not_imported_dynamic_elsewhere() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=False, dynamic_in_chain=True))
    assert result.status == "NOT_REACHABLE"
    assert "package not imported" in result.reasoning


def test_package_imported_unresolved() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=True, exact_node_exists=False))
    assert result.status == "POTENTIALLY_REACHABLE"
    assert "imported" in result.reasoning


def test_eval_in_chain() -> None:
    result = classifier.classify(_evidence(encountered_dynamic=True), _ctx(package_imported=True))
    assert result.status == "POTENTIALLY_REACHABLE"


def test_getattr_variable() -> None:
    result = classifier.classify(_evidence(), _ctx(package_imported=True, dynamic_in_chain=True))
    assert result.status == "POTENTIALLY_REACHABLE"


def test_never_false_negative_matrix() -> None:
    booleans = [False, True]
    for package_imported, exact, dynamic, unresolved, depth in itertools.product(
        booleans, repeat=5
    ):
        ctx = _ctx(
            package_imported=package_imported,
            exact_node_exists=exact,
            dynamic_in_chain=dynamic,
            unresolved_imports=unresolved,
            max_depth_exceeded=depth,
        )
        result = classifier.classify(_evidence(), ctx)
        # NOT_REACHABLE only when the analysis is fully certain (R2). An
        # unimported package is NOT_REACHABLE regardless of dynamic edges
        # elsewhere (matrix row 4).
        certain = (not package_imported and not unresolved) or (
            package_imported and exact and not dynamic and not unresolved
        )
        expected = "NOT_REACHABLE" if certain else "POTENTIALLY_REACHABLE"
        assert result.status == expected, (package_imported, exact, dynamic, unresolved, depth)


def test_reachable_wins_regardless_of_context() -> None:
    booleans = [False, True]
    for package_imported, exact, dynamic, unresolved, depth in itertools.product(
        booleans, repeat=5
    ):
        ctx = _ctx(
            package_imported=package_imported,
            exact_node_exists=exact,
            dynamic_in_chain=dynamic,
            unresolved_imports=unresolved,
            max_depth_exceeded=depth,
        )
        evidence = _evidence("REACHABLE", [["e", "pkg.func"]])
        assert classifier.classify(evidence, ctx).status == "REACHABLE"


def test_reasoning_non_empty() -> None:
    result = classifier.classify(_evidence(), _ctx())
    assert result.reasoning.strip()


def test_result_is_reachability_result() -> None:
    result = classifier.classify(_evidence(), _ctx())
    assert isinstance(result, ReachabilityResult)
    assert result.vulnerability.osv_id == "TEST-1"
