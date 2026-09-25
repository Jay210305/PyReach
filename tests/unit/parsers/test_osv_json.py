from pyreach.parsers.osv_json import (
    Vulnerability,
    extract_affected,
    is_version_affected,
    parse_osv_record,
)


def test_parse_valid_osv_record() -> None:
    record = {
        "id": "GHSA-1234-5678-9012",
        "summary": "Sample advisory",
        "aliases": ["CVE-2023-12345", "PYSEC-2023-1"],
        "published": "2023-05-20T10:00:00Z",
        "severity": [{"type": "CVSS_V3", "score": "8.5"}],
        "affected": [
            {
                "package": {"name": "requests", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "2.0.0"}, {"fixed": "2.31.0"}],
                    }
                ],
                "ecosystem_specific": {
                    "imports": [{"symbols": ["requests.sessions.Session.request"]}]
                },
            }
        ],
    }
    vuln = parse_osv_record(record)
    assert vuln is not None
    assert isinstance(vuln, Vulnerability)
    assert vuln.osv_id == "GHSA-1234-5678-9012"
    assert vuln.cve_id == "CVE-2023-12345"
    assert vuln.package_name == "requests"
    assert vuln.severity_score == 8.5
    assert vuln.severity_level == "HIGH"
    assert vuln.summary == "Sample advisory"
    assert vuln.affected_symbols == ["requests.sessions.Session.request"]
    assert vuln.version_introduced == "2.0.0"
    assert vuln.version_fixed == "2.31.0"


def test_skip_non_pypi_record() -> None:
    record = {
        "id": "GHSA-NPM-0001",
        "affected": [{"package": {"name": "express", "ecosystem": "npm"}}],
    }
    assert parse_osv_record(record) is None


def test_severity_mapping() -> None:
    from pyreach.parsers.osv_json import map_cvss_score_to_level

    assert map_cvss_score_to_level(9.8) == "CRITICAL"
    assert map_cvss_score_to_level(8.0) == "HIGH"
    assert map_cvss_score_to_level(5.5) == "MEDIUM"
    assert map_cvss_score_to_level(2.0) == "LOW"
    assert map_cvss_score_to_level(None) is None


def test_symbol_sentinel_when_absent() -> None:
    record = {
        "id": "GHSA-NO-SYMBOLS",
        "affected": [
            {
                "package": {"name": "flask", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "1.0.0"}, {"fixed": "2.0.0"}],
                    }
                ],
            }
        ],
    }
    vuln = parse_osv_record(record)
    assert vuln is not None
    assert vuln.affected_symbols == ["*"]


def test_extract_affected_multiple_symbols() -> None:
    record = {
        "id": "GHSA-MULTIPLE",
        "affected": [
            {
                "package": {"name": "urllib3", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "1.20.0"}, {"fixed": "1.26.5"}],
                    }
                ],
                "ecosystem_specific": {
                    "imports": [{"symbols": ["urllib3.poolmanager.PoolManager", "urllib3.request"]}]
                },
            }
        ],
    }
    items = extract_affected(record)
    symbols = [s[0] for s in items]
    assert symbols == ["urllib3.poolmanager.PoolManager", "urllib3.request"]
    assert items[0][1] == "1.20.0"
    assert items[0][2] == "1.26.5"


def test_is_version_affected_truth_table() -> None:
    # Standard range [1.0.0, 2.0.0)
    assert is_version_affected("1.5.0", "1.0.0", "2.0.0") is True
    assert is_version_affected("1.0.0", "1.0.0", "2.0.0") is True
    assert is_version_affected("0.9.0", "1.0.0", "2.0.0") is False
    assert is_version_affected("2.0.0", "1.0.0", "2.0.0") is False
    assert is_version_affected("2.1.0", "1.0.0", "2.0.0") is False

    # Only introduced [1.0.0, infinity)
    assert is_version_affected("1.0.0", "1.0.0", None) is True
    assert is_version_affected("9.9.9", "1.0.0", None) is True
    assert is_version_affected("0.5.0", "1.0.0", None) is False

    # Only fixed [0, 2.0.0)
    assert is_version_affected("1.0.0", None, "2.0.0") is True
    assert is_version_affected("2.0.0", None, "2.0.0") is False

    # Invalid versions resolve conservatively to True
    assert is_version_affected("not-a-valid-version", "1.0.0", "2.0.0") is True
    assert is_version_affected("1.0.0", "invalid-introduced", "2.0.0") is True


def test_malformed_record_returns_none() -> None:
    assert parse_osv_record({}) is None
    assert parse_osv_record({"id": "GHSA-1"}) is None
    assert parse_osv_record({"id": "GHSA-2", "affected": []}) is None


def test_parse_null_aliases_and_empty_severity() -> None:
    record = {
        "id": "GHSA-NULL-ALIASES",
        "aliases": None,
        "severity": [],
        "affected": [
            {
                "package": {"name": "django", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "3.2.0"}, {"fixed": "3.2.19"}],
                    }
                ],
            }
        ],
    }
    vuln = parse_osv_record(record)
    assert vuln is not None
    assert vuln.cve_id is None
    assert vuln.severity_score is None
    assert vuln.severity_level is None
    assert vuln.package_name == "django"


def test_last_affected_range_handling() -> None:
    record = {
        "id": "GHSA-LAST-AFFECTED",
        "affected": [
            {
                "package": {"name": "cryptography", "ecosystem": "PyPI"},
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [{"introduced": "3.0.0"}, {"last_affected": "3.4.7"}],
                    }
                ],
            }
        ],
    }
    items = extract_affected(record)
    assert len(items) == 1
    assert items[0][1] == "3.0.0"
    assert items[0][2] == "3.4.7"


def test_ecosystem_specific_fallback_symbols() -> None:
    record = {
        "id": "GHSA-FALLBACK-SYMBOLS",
        "affected": [
            {
                "package": {"name": "werkzeug", "ecosystem": "PyPI"},
                "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}],
                "ecosystem_specific": {"symbols": ["werkzeug.debug.DebuggedApplication"]},
            }
        ],
    }
    items = extract_affected(record)
    assert len(items) == 1
    assert items[0][0] == "werkzeug.debug.DebuggedApplication"


def test_sample_osv_record_fixture(sample_osv_record: dict[str, object]) -> None:
    vuln = parse_osv_record(sample_osv_record)  # type: ignore[arg-type]
    assert vuln is not None
    assert vuln.package_name == "requests"
    assert vuln.cve_id == "CVE-2023-32681"
    assert len(vuln.affected_symbols) == 2
