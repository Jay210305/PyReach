# Testing Strategy

## 1. Testing Philosophy

PyReach follows **Test-Driven Development (TDD)** and **Behavior-Driven Development (BDD)** principles:
- Write failing tests before implementing features.
- Tests serve as executable specifications.
- Aim for >=80% code coverage with emphasis on critical paths (parsers, AST engine, reachability analyzer).
- Use parametrized tests to cover edge cases systematically.

## 2. Test Pyramid

```
       /\
      /  \     E2E / Integration (5%)
     /----\     - Full scan on synthetic projects
    /      \    - CI pipeline validation
   /--------\   Integration (15%)
  /          \  - Multi-module call graph building
 /------------\ Unit Tests (80%)
/              \- Individual functions, classes, edge cases
```

## 3. Test Environment

### Tools
| Tool | Purpose | Version |
|------|---------|---------|
| pytest | Test runner, fixtures, parametrization | >=7.0 |
| pytest-cov | Coverage reporting | >=4.0 |
| pytest-xdist | Parallel test execution | >=3.0 |
| factory-boy | Test data generation | >=3.3 |
| freezegun | Date/time mocking | >=1.0 |

### Directory Structure
```
tests/
├── conftest.py                 # Shared fixtures, hooks
├── unit/
│   ├── __init__.py
│   ├── parsers/
│   │   ├── test_manifest.py
│   │   └── test_osv_json.py
│   ├── ast/
│   │   ├── test_builder.py
│   │   ├── test_symbols.py
│   │   └── test_resolver.py
│   ├── callgraph/
│   │   ├── test_engine.py
│   │   └── test_nodes.py
│   ├── reachability/
│   │   ├── test_analyzer.py
│   │   └── test_classifier.py
│   └── output/
│       └── test_sarif.py
├── integration/
│   ├── __init__.py
│   ├── test_end_to_end.py
│   └── test_callgraph_integration.py
├── fixtures/
│   ├── projects/               # Synthetic Python projects
│   │   ├── vulnerable_flask/
│   │   ├── clean_fastapi/
│   │   └── dynamic_imports/
│   ├── osv_records/            # Sample OSV JSON records
│   └── sarif_schema/           # Cached SARIF v2.1.0 schema
└── e2e/
    └── test_cli_invocations.py
```

## 4. Unit Testing Plan

### 4.1 Manifest Parser Tests (`tests/unit/parsers/test_manifest.py`)

**Fixture: `sample_requirements_txt`**
```python
@pytest.fixture
def sample_requirements_txt(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("""
requests==2.31.0
flask>=2.0.0
numpy[extras]>=1.24.0; python_version >= "3.10"
-e git+https://github.com/user/repo.git#egg=private_pkg
# This is a comment
    """)
    return req
```

**Test Cases:**
| Test Name | Input | Expected Result |
|-----------|-------|-----------------|
| `test_parse_simple_package` | `requests==2.31.0` | `Dependency("requests", "2.31.0", ...)` |
| `test_parse_version_range` | `flask>=2.0.0` | `Dependency("flask", "2.0.0", ...)` with comparator info |
| `test_parse_with_extra` | `numpy[extras]` | `extra="extras"` |
| `test_parse_with_marker` | `...; python_version >= "3.10"` | `marker` field populated |
| `test_parse_editable_install` | `-e git+...` | Skipped or flagged as non-PyPI |
| `test_parse_comment_ignored` | `# comment` | Ignored |
| `test_parse_empty_line` | `\n` | Ignored |
| `test_parse_file_not_found` | Missing file | Raises `ConfigError` |

### 4.2 AST Builder Tests (`tests/unit/ast/test_builder.py`)

**Fixture: `sample_module_source`**
```python
@pytest.fixture
def sample_module_source():
    return '''
import os
import numpy as np
from collections import OrderedDict as OD
from . import sibling

def greet(name):
    return f"Hello, {name}"

class Greeter:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return greet(self.name)
'''
```

**Test Cases:**
| Test Name | Assertion |
|-----------|-----------|
| `test_build_module_ast` | Returns `ModuleAST` with valid AST tree |
| `test_symbol_table_import` | `symbol_table["os"] == "os"` |
| `test_symbol_table_alias` | `symbol_table["np"] == "numpy"` |
| `test_symbol_table_from_import_alias` | `symbol_table["OD"] == "collections.OrderedDict"` |
| `test_relative_import` | `symbol_table["sibling"] == "current_pkg.sibling"` |
| `test_syntax_error_handling` | Invalid syntax raises `ParseError`, does not crash |

### 4.3 Call Graph Engine Tests (`tests/unit/callgraph/test_engine.py`)

**Synthetic Project Fixture:**
```python
@pytest.fixture
def linear_call_project(tmp_path):
    (tmp_path / "main.py").write_text('''
from utils import helper

def main():
    helper()
''')
    (tmp_path / "utils.py").write_text('''
def helper():
    print("help")
''')
    return tmp_path
```

**Test Cases:**
| Test Name | Assertion |
|-----------|-----------|
| `test_build_nodes` | Nodes exist for `main.main` and `utils.helper` |
| `test_build_static_edge` | Edge `main.main -> utils.helper` with type `STATIC` |
| `test_detect_dynamic_edge` | `eval("foo()")` creates `DYNAMIC` edge |
| `test_self_method_resolution` | `self.method()` resolves to current class method |
| `test_inheritance_edge` | Subclass method override creates `INHERITANCE` edge to parent |
| `test_unresolved_call` | Unresolved name creates `DYNAMIC` edge with confidence 0.3 |

### 4.4 Reachability Analyzer Tests (`tests/unit/reachability/test_analyzer.py`)

**Graph Fixture:**
```python
@pytest.fixture
def simple_graph():
    G = nx.DiGraph()
    G.add_node("main.app", node_type="FUNCTION")
    G.add_node("myapp.client.fetch", node_type="METHOD")
    G.add_node("requests.get", node_type="FUNCTION")
    G.add_edge("main.app", "myapp.client.fetch", edge_type="STATIC")
    G.add_edge("myapp.client.fetch", "requests.get", edge_type="STATIC")
    return G
```

**Test Cases:**
| Test Name | Setup | Expected Status |
|-----------|-------|-----------------|
| `test_reachable_direct` | Entry=`main.app`, Symbol=`requests.get` | `REACHABLE` |
| `test_not_reachable` | Entry=`main.app`, Symbol=`os.system` (no edge) | `NOT_REACHABLE` |
| `test_potentially_reachable_dynamic` | Edge `myapp.client.fetch -> os.system` is `DYNAMIC` | `POTENTIALLY_REACHABLE` |
| `test_depth_limit_exceeded` | Path length 6, max_depth=5 | `NOT_REACHABLE` |
| `test_cycle_handling` | Recursive mutual calls A->B->A | Terminates, does not infinite loop |
| `test_memoization` | Same entry+symbol queried twice | Second call uses cache |

## 5. Integration Testing Plan

### 5.1 End-to-End Scan Tests (`tests/integration/test_end_to_end.py`)

**Scenario 1: Vulnerable Flask App**
- Project with Flask 2.0.0 and a known CVE in Werkzeug.
- Application defines routes that call vulnerable Werkzeug function.
- **Assert**: PyReach reports `REACHABLE` with correct path and valid SARIF.

**Scenario 2: Clean FastAPI App**
- Project with FastAPI and no vulnerable dependencies.
- **Assert**: PyReach exits 0, SARIF contains zero results.

**Scenario 3: Dynamic Import Project**
- Project using `importlib.import_module` to load plugins.
- Vulnerable function in plugin module.
- **Assert**: PyReach reports `POTENTIALLY_REACHABLE` due to dynamic edge.

**Scenario 4: Transitive Non-Reachable**
- Project depends on `requests`, which depends on `urllib3`.
- App uses `requests.get` but never touches `urllib3` internals directly.
- CVE exists in `urllib3` function not on call path.
- **Assert**: PyReach reports `NOT_REACHABLE` for that CVE.

### 5.2 SARIF Validation Integration Test

```python
def test_sarif_output_validates_against_schema(tmp_path):
    project = create_synthetic_project(tmp_path, scenario="reachable")
    output = tmp_path / "out.sarif"
    run_pyreach([str(project), "-o", str(output)])
    assert output.exists()
    sarif = json.loads(output.read_text())
    jsonschema.validate(sarif, load_sarif_schema())
```

## 6. E2E / CLI Testing Plan (`tests/e2e/test_cli_invocations.py`)

Use `subprocess.run` to invoke the installed CLI and verify behavior:

| Test | Command | Expected Behavior |
|------|---------|-------------------|
| `test_cli_help` | `pyreach --help` | Exit 0, usage text contains all options |
| `test_cli_version` | `pyreach --version` | Exit 0, outputs `PyReach 0.1.0` |
| `test_cli_missing_manifest` | `pyreach /empty/dir` | Exit 2, error mentions missing manifest |
| `test_cli_reachable_fails` | `pyreach /vuln_project` | Exit 1, SARIF contains error-level results |
| `test_cli_no_fail` | `pyreach --no-fail /vuln_project` | Exit 0 despite reachable CVEs |
| `test_cli_text_format` | `pyreach -f text /project` | Exit 0, stdout contains human-readable summary |

## 7. Coverage Goals and Enforcement

### Minimum Thresholds
- **Overall project**: >=80% line coverage
- **Critical modules**:
  - `parsers/`: >=90%
  - `ast/`: >=85%
  - `callgraph/`: >=85%
  - `reachability/`: >=85%
  - `output/sarif.py`: >=80%

### CI Enforcement
```yaml
# .gitlab-ci.yml snippet
test:
  stage: test
  script:
    - uv run pytest --cov=pyreach --cov-report=xml --cov-fail-under=80
  coverage: '/TOTAL.+\s(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

## 8. Test Data Management

### Synthetic Projects
Located in `tests/fixtures/projects/`, each is a self-contained Python project:

```
tests/fixtures/projects/
├── vulnerable_flask/
│   ├── requirements.txt
│   ├── src/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── routes.py
│   └── README.md
├── clean_fastapi/
│   ├── requirements.txt
│   └── src/
│       └── main.py
└── dynamic_imports/
    ├── requirements.txt
    ├── src/
    │   ├── main.py
    │   └── plugins/
    └── plugins/
        └── vuln_plugin.py
```

### OSV Test Records
Small subset of real OSV records (public domain / CC0) stored in `tests/fixtures/osv_records/` for fast, deterministic tests without downloading full dumps.

## 9. Performance Regression Tests

Located in `tests/performance/` (run manually or on scheduled CI):

```python
@pytest.mark.performance
def test_scan_completes_under_45s():
    start = time.monotonic()
    run_pyreach([LIDERCOM_LARGEST_PROJECT])
    elapsed = time.monotonic() - start
    assert elapsed < 45.0, f"Scan took {elapsed:.1f}s, exceeding 45s threshold"
```

## 10. Bug Triage and Regression Prevention

- Every bug fix must include a regression test reproducing the original issue.
- Use `pytest.mark.xfail` for known unresolved issues to track them without breaking CI.
- Maintain a `BUGFIX.md` log linking bug reports to their regression test cases.

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
