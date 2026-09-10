# Technical Specifications

## 1. Environment Specification

### Minimum Requirements
- Python 3.10 or higher (CPython implementation)
- 4 GB RAM (8 GB recommended for large dependency trees)
- 500 MB disk space for OSV SQLite database
- POSIX-compatible filesystem or Windows NTFS

### Development Environment Setup
```bash
# Clone repository
git clone <repo-url> pyreach
cd pyreach

# Install Poetry if not present
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and create virtual environment
poetry install --with dev

# Activate shell
poetry shell

# Verify installation
pyreach --version
```

### Poetry pyproject.toml Snippet
```toml
[tool.poetry]
name = "pyreach"
version = "0.1.0"
description = "Static reachability analysis for Python dependency vulnerabilities"
authors = ["Julio Centeno <...>", "Jose Alonso Yanez <...>"]
readme = "README.md"
license = "MIT"

[tool.poetry.dependencies]
python = "^3.10"
networkx = "^3.0"
jsonschema = "^4.0"
packaging = "^23.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"
black = "^23.0"
mypy = "^1.0"
ruff = "^0.1.0"

[tool.poetry.scripts]
pyreach = "pyreach.cli:main"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## 2. Package Structure

```
pyreach/
├── __init__.py
├── cli.py                          # Entry point, argument parsing, exit codes
├── config.py                       # Configuration dataclasses, .pyreach.yml loader
├── exceptions.py                   # Custom exception hierarchy
├── logger.py                       # Structured logging setup
├── parsers/
│   ├── __init__.py
│   ├── manifest.py                 # requirements.txt, Pipfile.lock parsing
│   └── osv_json.py                 # OSV JSON record parser
├── loaders/
│   ├── __init__.py
│   ├── source.py                   # Application .py file discovery
│   └── packages.py                 # site-packages path resolution
├── osv/
│   ├── __init__.py
│   ├── mapper.py                   # Advisory lookup by package/version
│   └── importer.py                 # Bulk OSV JSON -> SQLite ingestion
├── ast/
│   ├── __init__.py
│   ├── builder.py                  # ast.parse wrapper + metadata
│   ├── symbols.py                  # Symbol table construction
│   └── resolver.py                 # Import alias resolution
├── callgraph/
│   ├── __init__.py
│   ├── engine.py                   # DiGraph construction from ASTs
│   ├── nodes.py                    # Node dataclasses (Function, Method, Class)
│   └── edges.py                    # Edge classification (STATIC, DYNAMIC, ...)
├── reachability/
│   ├── __init__.py
│   ├── analyzer.py                 # BFS/DFS bounded traversal
│   ├── classifier.py               # REACHABLE / NOT_REACHABLE / POTENTIALLY_REACHABLE
│   └── entrypoints.py              # Entry point detection / configuration
├── output/
│   ├── __init__.py
│   ├── sarif.py                    # SARIF v2.1.0 JSON builder
│   └── summary.py                  # Plain-text / stdout formatter
└── db/
    ├── __init__.py
    ├── connection.py               # SQLite context manager
    ├── schema.sql                  # DDL script
    └── migrations/                 # Future schema versioning
```

## 3. Data Contracts & Interfaces

### 3.1 Manifest Parser Output

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Dependency:
    name: str                         # Normalized package name, e.g., "requests"
    version: str                      # Installed version, e.g., "2.31.0"
    source: str                       # "requirements.txt" or "Pipfile.lock"
    extra: Optional[str] = None       # e.g., "security"
    marker: Optional[str] = None      # Environment marker string
```

### 3.2 AST Module Output

```python
from dataclasses import dataclass
import ast
from typing import Dict, Optional

@dataclass
class ModuleAST:
    file_path: str
    module_fqn: str                   # Fully qualified module name
    tree: ast.AST
    symbol_table: Dict[str, str]      # local_alias -> fully_qualified_name
    imports: Dict[str, str]           # imported_name -> source_module
```

### 3.3 Call Graph Node & Edge

```python
from dataclasses import dataclass
from typing import Optional, Literal

EdgeType = Literal["STATIC", "DYNAMIC", "INHERITANCE", "IMPORT"]

@dataclass(frozen=True)
class CGNode:
    fqn: str                          # "package.module.Class.method"
    file_path: Optional[str]
    line_number: Optional[int]
    node_type: Literal["FUNCTION", "METHOD", "CLASS", "LAMBDA"]

@dataclass(frozen=True)
class CGEdge:
    caller: CGNode
    callee: CGNode
    edge_type: EdgeType
    confidence: float = 1.0           # 0.0 - 1.0
```

### 3.4 Vulnerability Record

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Vulnerability:
    osv_id: str
    cve_id: Optional[str]
    package_name: str
    severity_score: Optional[float]
    severity_level: Optional[str]     # LOW, MEDIUM, HIGH, CRITICAL
    summary: str
    affected_symbols: List[str]       # ["package.module.vuln_func"]
    version_introduced: Optional[str]
    version_fixed: Optional[str]
```

### 3.5 Reachability Result

```python
from dataclasses import dataclass
from typing import List, Optional, Literal

ReachabilityStatus = Literal["REACHABLE", "NOT_REACHABLE", "POTENTIALLY_REACHABLE"]

@dataclass
class ReachabilityResult:
    vulnerability: Vulnerability
    status: ReachabilityStatus
    entry_points_reached: List[str]   # Which entry points have paths
    paths: List[List[str]]            # List of node_fqn paths (for REACHABLE)
    reasoning: str                    # Human-readable explanation
```

## 4. CLI Specification

### Command Syntax
```
pyreach [OPTIONS] <PROJECT_PATH>
```

### Arguments
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PROJECT_PATH` | string | Yes | Root directory of the Python project to analyze |

### Options
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--manifest` | `-m` | string | `requirements.txt` | Path to dependency manifest |
| `--db-path` | `-d` | string | `~/.pyreach/osv.db` | Path to local OSV SQLite database |
| `--output` | `-o` | string | `pyreach-results.sarif` | Output SARIF file path |
| `--entry-point` | `-e` | string (multi) | auto-detect | Additional entry point function FQNs |
| `--max-depth` | `-k` | int | `5` | Maximum call graph traversal depth |
| `--include-potentially` | | flag | False | Include POTENTIALLY_REACHABLE in failure exit code |
| `--no-fail` | | flag | False | Always exit 0 regardless of findings |
| `--format` | `-f` | string | `sarif` | Output format: `sarif`, `json`, `text` |
| `--verbose` | `-v` | flag | False | Enable debug logging |
| `--version` | | flag | False | Show version and exit |

### Exit Codes
| Code | Meaning | CI/CD Behavior |
|------|---------|----------------|
| 0 | Success: no reachable vulnerabilities (or `--no-fail`) | Pipeline continues |
| 1 | Reachable (and optionally potentially reachable) vulnerabilities found | Pipeline blocked |
| 2 | Configuration or runtime error | Pipeline blocked (infra issue) |

### Example Invocations

```bash
# Basic scan
pyreach /path/to/project

# Custom entry points for a FastAPI app
pyreach /path/to/project \
  -e "main.app" \
  -e "api.routes.health_check" \
  -o results.sarif

# Text output for local debugging
pyreach /path/to/project -f text --verbose

# CI mode: fail on potentially reachable as well
pyreach /path/to/project --include-potentially -o sarif/output.sarif
```

## 5. Configuration File (.pyreach.yml)

Projects may include a `.pyreach.yml` file to declare persistent configuration:

```yaml
pyreach:
  version: "1"
  entry_points:
    - "myapp.cli:main"
    - "myapp.api:init_routes"
  ignore_paths:
    - "tests/"
    - "docs/"
    - "scripts/"
  max_depth: 5
  manifest: "requirements.txt"
  osv_db: "~/.pyreach/osv.db"
  thresholds:
    fail_on_reachable: true
    fail_on_potentially: false
```

## 6. OSV Data Ingestion Specification

### Source Format
OSV JSON records conforming to OpenSSF OSV Schema v1.6.0.

### Ingestion Pipeline
1. Download OSV export for PyPI ecosystem (or use pre-downloaded dump).
2. Stream-parse JSONL file to avoid loading entire dataset into memory.
3. Filter records where `affected[].package.ecosystem == "PyPI"`.
4. Normalize package names (PEP 503 normalization: lowercase, underscore/hyphen collapsed).
5. Extract affected version ranges and symbols.
6. Upsert into SQLite `advisories` and `affected_symbols` tables.

### Update Cadence
- Weekly cron job on CI runner or developer workstation.
- Incremental: only process records with `modified` timestamp newer than last sync.

## 7. SARIF Output Specification

### Minimum Valid SARIF Document Structure

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "PyReach",
          "version": "0.1.0",
          "informationUri": "https://github.com/lidercom/pyreach",
          "rules": [
            {
              "id": "PYREACH-REACHABLE-CVE",
              "name": "ReachableVulnerability",
              "shortDescription": { "text": "A vulnerable dependency symbol is reachable from application code." },
              "defaultConfiguration": { "level": "error" }
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "PYREACH-REACHABLE-CVE",
          "level": "error",
          "message": { "text": "CVE-2023-XXXX in requests==2.31.0: requests.sessions.Session.request is REACHABLE from main.app" },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": { "uri": "src/main.py" },
                "region": { "startLine": 42 }
              }
            }
          ],
          "codeFlows": [
            {
              "threadFlows": [
                {
                  "locations": [
                    { "location": { "message": { "text": "Entry point: main.app" } } },
                    { "location": { "message": { "text": "-> myapp.client.fetch" } } },
                    { "location": { "message": { "text": "-> requests.sessions.Session.request (VULNERABLE)" } } }
                  ]
                }
              ]
            }
          ],
          "properties": {
            "reachability": "REACHABLE",
            "cveId": "CVE-2023-XXXX",
            "packageName": "requests",
            "installedVersion": "2.31.0",
            "severity": "HIGH"
          }
        }
      ]
    }
  ]
}
```

### SARIF Mapping Rules

| PyReach Concept | SARIF Element |
|-----------------|---------------|
| Tool metadata | `runs[].tool.driver` |
| Vulnerability rule | `runs[].tool.driver.rules[]` |
| Each result | `runs[].results[]` |
| Reachable | `result.level = "error"` |
| Potentially Reachable | `result.level = "warning"` |
| Not Reachable | Omitted or `result.level = "note"` |
| Call path | `result.codeFlows[].threadFlows[].locations[]` |
| Custom metadata | `result.properties` object |

## 8. Error Handling Strategy

### Exception Hierarchy

```
PyReachError (base)
├── ConfigError          # Invalid .pyreach.yml, missing manifest
├── ParseError           # Malformed requirements.txt, invalid Python syntax
├── OSVError             # Missing OSV DB, corrupt record
├── AnalysisError        # AST or Call Graph construction failure
└── OutputError          # SARIF serialization or file write failure
```

### Handling Rules
- **ParseError on a single file**: Log warning, skip file, continue analysis (do not fail entire scan).
- **Missing OSV DB**: Exit code 2 with explicit message instructing user to run `pyreach-osv-sync`.
- **No entry points found**: Exit code 2 with suggestion to use `-e` flag.
- **Memory exhaustion during graph build**: Catch `MemoryError`, suggest `--max-depth` reduction or `--exclude-packages`.

## 9. Logging Specification

- **Levels**: DEBUG (AST traversal details), INFO (progress), WARNING (skipped files), ERROR (fatal blockers).
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Outputs**: stderr (default), file (`--log-file`), or JSON structured logs (CI mode).

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
