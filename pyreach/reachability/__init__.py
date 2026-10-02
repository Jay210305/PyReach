"""Reachability analysis package."""

from pyreach.reachability.analyzer import analyze_reachability, clear_cache
from pyreach.reachability.classifier import ReachabilityClassifier, SymbolContext
from pyreach.reachability.contracts import (
    MAX_PATHS,
    ReachabilityResult,
    ReachabilityStatus,
    TraversalOutcome,
)
from pyreach.reachability.entrypoints import (
    EntryPointDetector,
    detect_or_fail,
    resolve_entry_points,
)

__all__ = [
    "EntryPointDetector",
    "MAX_PATHS",
    "ReachabilityClassifier",
    "ReachabilityResult",
    "ReachabilityStatus",
    "SymbolContext",
    "TraversalOutcome",
    "analyze_reachability",
    "clear_cache",
    "detect_or_fail",
    "resolve_entry_points",
]
