"""Deterministic stub advisory source for integration tests.

Provides a single synthetic :class:`~pyreach.osv.mapper.Vulnerability`
so reachability scenarios never depend on real CVE data or the network. The
advisory points at ``vuln_lib.risky``, the vulnerable function in the synthetic
``vuln_lib`` stub package used by every project under
``tests/fixtures/projects/``.
"""

from pyreach.osv.mapper import Vulnerability

VULN_SYMBOL = "vuln_lib.risky"


def stub_advisory() -> Vulnerability:
    """Return the synthetic advisory exercised by the S3-T8 scenarios."""
    return Vulnerability(
        osv_id="GHSA-SYNTH-0001",
        cve_id="CVE-2026-00001",
        package_name="vuln_lib",
        severity_score=9.8,
        severity_level="CRITICAL",
        summary="Synthetic vulnerable function in the vuln_lib stub package.",
        affected_symbols=[VULN_SYMBOL],
        version_introduced="1.0.0",
        version_fixed="2.0.0",
    )
