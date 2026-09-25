from pathlib import Path

import pytest

from pyreach.exceptions import ConfigError, ParseError
from pyreach.parsers.manifest import (
    SOURCE_REQUIREMENTS_TXT,
    Dependency,
    ManifestParser,
    RequirementsTxtParser,
)


def _write_req(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "requirements.txt"
    p.write_text(content, encoding="utf-8")
    return p


def test_requirements_parser_implements_protocol() -> None:
    parser = RequirementsTxtParser()
    assert isinstance(parser, ManifestParser)
    assert parser.source_name == SOURCE_REQUIREMENTS_TXT
    assert parser.supports(Path("requirements.txt")) is True
    assert parser.supports(Path("other/requirements.txt")) is True
    assert parser.supports(Path("Pipfile.lock")) is False


def test_parse_simple_package(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "requests==2.31.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_pinned_with_spaces(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "requests == 2.31.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_version_range_lower_bound(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "flask>=2.0.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="flask", version="2.0.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_version_compatible(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "flask~=2.0.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="flask", version="2.0.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_upper_bound_only(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "flask<3.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="flask", version="", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_with_extras(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "numpy[extras]>=1.24.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [
        Dependency(
            name="numpy",
            version="1.24.0",
            source=SOURCE_REQUIREMENTS_TXT,
            extra="extras",
        )
    ]


def test_parse_multiple_extras(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "uvicorn[standard,reload]\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [
        Dependency(
            name="uvicorn",
            version="",
            source=SOURCE_REQUIREMENTS_TXT,
            extra="standard,reload",
        )
    ]


def test_parse_with_marker(tmp_path: Path) -> None:
    p = _write_req(tmp_path, 'x==1; python_version >= "3.10"\n')
    deps = RequirementsTxtParser().parse(p)
    assert deps == [
        Dependency(
            name="x",
            version="1",
            source=SOURCE_REQUIREMENTS_TXT,
            marker='python_version >= "3.10"',
        )
    ]


def test_parse_editable_install_flagged(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "-e git+https://github.com/user/repo.git#egg=private_pkg\n")
    default_parser = RequirementsTxtParser(include_non_pypi=False)
    assert default_parser.parse(p) == []

    non_pypi_parser = RequirementsTxtParser(include_non_pypi=True)
    assert non_pypi_parser.parse(p) == [
        Dependency(name="private-pkg", version="", source=SOURCE_REQUIREMENTS_TXT)
    ]


def test_parse_comment_ignored(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "# This is a comment\n# another comment\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == []


def test_parse_inline_comment(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "requests==2.31.0  # exact pin\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_empty_lines(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "\n\n   \n\t\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == []


def test_parse_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent_requirements.txt"
    with pytest.raises(ConfigError) as exc_info:
        RequirementsTxtParser().parse(missing)
    assert str(missing) in str(exc_info.value)


def test_parse_malformed_line(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "===bad===\n")
    with pytest.raises(ParseError) as exc_info:
        RequirementsTxtParser().parse(p)
    assert "===bad===" in str(exc_info.value)


def test_parse_hash_option(tmp_path: Path) -> None:
    content = "requests==2.31.0 --hash=sha256:2910d69be4019a86a63dca8c531d05fa\n"
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_line_continuation(tmp_path: Path) -> None:
    content = "requests==\\\n    2.31.0\n"
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_index_url_skipped(tmp_path: Path) -> None:
    content = (
        "--index-url https://pypi.org/simple\n"
        "--extra-index-url https://custom.pypi/simple\n"
        "--find-links /tmp/wheelhouse\n"
        "--trusted-host custom.pypi\n"
        "requests==2.31.0\n"
    )
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_duplicate_keeps_last(tmp_path: Path) -> None:
    content = "requests==2.28.0\nflask==2.0.0\nrequests==2.31.0\n"
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [
        Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT),
        Dependency(name="flask", version="2.0.0", source=SOURCE_REQUIREMENTS_TXT),
    ]


def test_parse_url_requirement(tmp_path: Path) -> None:
    content = "https://example.com/packages/pkg-1.0.0-py3-none-any.whl\n"
    p = _write_req(tmp_path, content)
    default_parser = RequirementsTxtParser(include_non_pypi=False)
    assert default_parser.parse(p) == []

    non_pypi_parser = RequirementsTxtParser(include_non_pypi=True)
    assert non_pypi_parser.parse(p) == [
        Dependency(name="pkg", version="1.0.0", source=SOURCE_REQUIREMENTS_TXT)
    ]


def test_normalization_applied(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "Foo_Bar.Baz==1.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="foo-bar-baz", version="1.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_utf8_bom(tmp_path: Path) -> None:
    p = tmp_path / "requirements.txt"
    p.write_bytes(b"\xef\xbb\xbfrequests==2.31.0\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_archive_tar_and_zip(tmp_path: Path) -> None:
    content = (
        "https://example.com/tarballs/foo-bar-2.3.1.tar.gz\n"
        "https://example.com/zips/baz-qux-0.4.zip\n"
    )
    p = _write_req(tmp_path, content)
    parser = RequirementsTxtParser(include_non_pypi=True)
    deps = parser.parse(p)
    assert deps == [
        Dependency(name="foo-bar", version="2.3.1", source=SOURCE_REQUIREMENTS_TXT),
        Dependency(name="baz-qux", version="0.4", source=SOURCE_REQUIREMENTS_TXT),
    ]


def test_parse_hash_only_line(tmp_path: Path) -> None:
    content = "requests==2.31.0\n--hash=sha256:123456\n"
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_line_continuation_at_eof(tmp_path: Path) -> None:
    content = "requests==2.31.0\\\n"
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_pip_equals_options(tmp_path: Path) -> None:
    content = (
        "--index-url=https://pypi.org/simple\n"
        "--extra-index-url=https://other.pypi/simple\n"
        "requests==2.31.0\n"
    )
    p = _write_req(tmp_path, content)
    deps = RequirementsTxtParser().parse(p)
    assert deps == [Dependency(name="requests", version="2.31.0", source=SOURCE_REQUIREMENTS_TXT)]


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "manifests"


@pytest.mark.parametrize(
    ("input_line", "expected"),
    [
        ("requests==2.31.0", Dependency("requests", "2.31.0", SOURCE_REQUIREMENTS_TXT)),
        ("requests == 2.31.0", Dependency("requests", "2.31.0", SOURCE_REQUIREMENTS_TXT)),
        ("flask >= 2.0.0", Dependency("flask", "2.0.0", SOURCE_REQUIREMENTS_TXT)),
        ("flask ~= 2.0.0", Dependency("flask", "2.0.0", SOURCE_REQUIREMENTS_TXT)),
        ("flask < 3.0", Dependency("flask", "", SOURCE_REQUIREMENTS_TXT)),
        (
            "numpy[extra] >= 1.24.0",
            Dependency("numpy", "1.24.0", SOURCE_REQUIREMENTS_TXT, extra="extra"),
        ),
        (
            "uvicorn[standard,reload] == 0.20.0",
            Dependency("uvicorn", "0.20.0", SOURCE_REQUIREMENTS_TXT, extra="standard,reload"),
        ),
        (
            'urllib3 == 2.0.0; python_version >= "3.10"',
            Dependency(
                "urllib3", "2.0.0", SOURCE_REQUIREMENTS_TXT, marker='python_version >= "3.10"'
            ),
        ),
        ("Foo_Bar.Baz == 1.2.3", Dependency("foo-bar-baz", "1.2.3", SOURCE_REQUIREMENTS_TXT)),
    ],
)
def test_parametrized_requirements_parsing(
    tmp_path: Path, input_line: str, expected: Dependency
) -> None:
    p = _write_req(tmp_path, input_line + "\n")
    deps = RequirementsTxtParser().parse(p)
    assert deps == [expected]


def test_parse_crlf_line_endings(tmp_path: Path) -> None:
    p = tmp_path / "requirements.txt"
    p.write_bytes(b"requests==2.31.0\r\nflask>=2.2.0\r\n")
    deps = RequirementsTxtParser().parse(p)
    assert len(deps) == 2
    assert deps[0].name == "requests"
    assert deps[1].name == "flask"


def test_parse_local_wheel_path(tmp_path: Path) -> None:
    p = _write_req(tmp_path, "./dist/wheel_pkg-1.0.0-py3-none-any.whl\n")
    default_parser = RequirementsTxtParser(include_non_pypi=False)
    assert default_parser.parse(p) == []

    non_pypi_parser = RequirementsTxtParser(include_non_pypi=True)
    deps = non_pypi_parser.parse(p)
    assert deps == [Dependency(name="wheel-pkg", version="1.0.0", source=SOURCE_REQUIREMENTS_TXT)]


def test_parse_fixtures_from_disk() -> None:
    simple_file = FIXTURES_DIR / "requirements_simple.txt"
    simple_deps = RequirementsTxtParser().parse(simple_file)
    assert len(simple_deps) == 3
    assert [d.name for d in simple_deps] == ["requests", "flask", "urllib3"]

    empty_file = FIXTURES_DIR / "requirements_empty.txt"
    assert RequirementsTxtParser().parse(empty_file) == []

    complex_file = FIXTURES_DIR / "requirements_complex.txt"
    complex_deps = RequirementsTxtParser(include_non_pypi=True).parse(complex_file)
    names = [d.name for d in complex_deps]
    assert "click" in names
    assert "flask" in names
    assert "local-pkg" in names
    assert "requests" in names
    assert "wheel-pkg" in names


def test_conftest_fixtures(
    sample_requirements_txt: Path,
    make_requirements: pytest.FixtureRequest,
) -> None:
    deps = RequirementsTxtParser().parse(sample_requirements_txt)
    assert len(deps) == 4

    factory_req = make_requirements(["scipy==1.10.0", "pytest>=7.0.0"])  # type: ignore[operator]
    factory_deps = RequirementsTxtParser().parse(factory_req)
    assert len(factory_deps) == 2
