"""Shared reachability data contracts (spec §3.5, S3-T5/S3-T6).

These types are split out of the analyzer so the classifier (pure logic, no
NetworkX) can import them without a circular dependency on ``analyzer``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pyreach.osv.mapper import Vulnerability

ReachabilityStatus = Literal["REACHABLE", "NOT_REACHABLE", "POTENTIALLY_REACHABLE"]

MAX_PATHS = 5


@dataclass(frozen=True)
class TraversalOutcome:
    """Result of a bounded traversal toward a single symbol.

    ``status`` is the pair-level verdict for one entry point: ``REACHABLE``
    when a static path was found, ``POTENTIALLY_REACHABLE`` when no path was
    found but a dynamic/unresolved edge was crossed, otherwise
    ``NOT_REACHABLE``.
    """

    status: ReachabilityStatus
    paths: list[list[str]]
    encountered_dynamic: bool
    depth_exceeded: bool


@dataclass
class ReachabilityResult:
    """Per-symbol reachability verdict (spec §3.5)."""

    vulnerability: Vulnerability
    status: ReachabilityStatus
    entry_points_reached: list[str]
    paths: list[list[str]]
    reasoning: str
