# SARIF and CLI Design

## 1. SARIF v2.1.0 Output Design

### 1.1 Design Principles

- **Compliance**: Strict adherence to OASIS SARIF v2.1.0 schema to ensure ingestion by GitLab, GitHub Advanced Security, VS Code SARIF viewer, and other standard tools.
- **Extensibility**: Use `properties` objects for PyReach-specific metadata (reachability status, CVE details) without breaking standard consumers.
- **Traceability**: Include full call paths as `codeFlows` so developers can follow the execution chain from entry point to vulnerable symbol.

### 1.2 SARIF Document Structure

Every PyReach scan produces a single SARIF JSON file containing one `run`.

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
              "shortDescription": {
                "text": "A vulnerable dependency symbol is statically reachable from application code."
              },
              "fullDescription": {
                "text": "The application's call graph contains a directed path from a defined entry point to a function or method known to contain a security vulnerability. The vulnerable package version is installed and the code path is exploitable under static analysis assumptions."
              },
              "defaultConfiguration": {
                "level": "error"
              },
              "properties": {
                "category": "security",
                "precision": "high",
                "tags": ["security", "vulnerability", "reachability", "sca"]
              }
            },
            {
              "id": "PYREACH-POTENTIAL-CVE",
              "name": "PotentiallyReachableVulnerability",
              "shortDescription": {
                "text": "A vulnerable dependency symbol may be reachable via dynamic or unresolved call paths."
              },
              "defaultConfiguration": {
                "level": "warning"
              },
              "properties": {
                "category": "security",
                "precision": "medium",
                "tags": ["security", "vulnerability", "reachability", "dynamic"]
              }
            }
          ]
        }
      },
      "results": [],
      "invocations": [
        {
          "executionSuccessful": true,
          "arguments": ["pyreach", "/path/to/project", "-o", "results.sarif"],
          "workingDirectory": {
            "uri": "file:///path/to/project"
          }
        }
      ]
    }
  ]
}
```

### 1.3 Result Object Mapping

Each vulnerability classification becomes one `result` object.

#### REACHABLE Result Example

```json
{
  "ruleId": "PYREACH-REACHABLE-CVE",
  "ruleIndex": 0,
  "level": "error",
  "message": {
    "text": "CVE-2023-32681 in requests==2.31.0: requests.sessions.Session.request is REACHABLE from main.app"
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": {
          "uri": "src/myapp/client.py",
          "uriBaseId": "PROJECT_ROOT"
        },
        "region": {
          "startLine": 24,
          "startColumn": 9,
          "endColumn": 22
        }
      },
      "logicalLocations": [
        {
          "fullyQualifiedName": "myapp.client.ApiClient.fetch_data",
          "kind": "function"
        }
      ]
    }
  ],
  "codeFlows": [
    {
      "threadFlows": [
        {
          "locations": [
            {
              "location": {
                "physicalLocation": {
                  "artifactLocation": { "uri": "src/myapp/main.py" },
                  "region": { "startLine": 10 }
                },
                "message": { "text": "Entry point: main.app" }
              },
              "kinds": ["entryPoint"]
            },
            {
              "location": {
                "physicalLocation": {
                  "artifactLocation": { "uri": "src/myapp/main.py" },
                  "region": { "startLine": 12 }
                },
                "message": { "text": "-> myapp.client.ApiClient.fetch_data" }
              },
              "kinds": ["call"]
            },
            {
              "location": {
                "physicalLocation": {
                  "artifactLocation": { "uri": "src/myapp/client.py" },
                  "region": { "startLine": 24 }
                },
                "message": { "text": "-> requests.sessions.Session.request (VULNERABLE)" }
              },
              "kinds": ["vulnerableCall"]
            }
          ]
        }
      ]
    }
  ],
  "properties": {
    "reachability": "REACHABLE",
    "cveId": "CVE-2023-32681",
    "osvId": "GHSA-j8r2-6x6q-8qgp",
    "packageName": "requests",
    "installedVersion": "2.31.0",
    "severityScore": 7.5,
    "severityLevel": "HIGH",
    "pathDepth": 2
  }
}
```

#### POTENTIALLY REACHABLE Result Example

```json
{
  "ruleId": "PYREACH-POTENTIAL-CVE",
  "ruleIndex": 1,
  "level": "warning",
  "message": {
    "text": "CVE-2023-XXXX in django==4.2.0: django.core.handlers.base.BaseHandler._get_response is POTENTIALLY REACHABLE from main.app (unresolved dynamic import)"
  },
  "locations": [
    {
      "physicalLocation": {
        "artifactLocation": { "uri": "src/myapp/main.py" },
        "region": { "startLine": 15 }
      }
    }
  ],
  "properties": {
    "reachability": "POTENTIALLY_REACHABLE",
    "cveId": "CVE-2023-XXXX",
    "reason": "Dynamic import via importlib.import_module prevents static resolution"
  }
}
```

#### NOT REACHABLE Handling

By default, `NOT_REACHABLE` vulnerabilities are **omitted** from SARIF output to reduce noise. If `--include-all` is passed, they are included with `level: "note"` and `ruleId: "PYREACH-NOT-REACHABLE-CVE"`.

### 1.4 SARIF Validation Strategy

```python
# tests/test_sarif_output.py
import json
import jsonschema
import pytest
from pathlib import Path

SARIF_SCHEMA_URL = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"

def load_sarif_schema() -> dict:
    # Cache locally to avoid network calls in CI
    schema_path = Path("tests/fixtures/sarif-schema-2.1.0.json")
    if schema_path.exists():
        return json.loads(schema_path.read_text())
    # Fallback: fetch once and save
    import urllib.request
    with urllib.request.urlopen(SARIF_SCHEMA_URL) as response:
        schema = json.load(response)
    schema_path.write_text(json.dumps(schema))
    return schema

def test_sarif_output_is_valid(tmp_path):
    output_file = tmp_path / "output.sarif"
    # ... run pyreach to generate output_file ...
    sarif_data = json.loads(output_file.read_text())
    schema = load_sarif_schema()
    jsonschema.validate(instance=sarif_data, schema=schema)
```

### 1.5 Artifact Location Base URI

To make SARIF portable across different machines:
- Set `uriBaseId`: `PROJECT_ROOT` mapped to the absolute path of the scanned project.
- All `artifactLocation.uri` values are relative to `PROJECT_ROOT`.

```json
"originalUriBaseIds": {
  "PROJECT_ROOT": {
    "uri": "file:///home/user/projects/myapp/"
  }
}
```

## 2. CLI Design

### 2.1 Command Structure

```
pyreach [GLOBAL_OPTIONS] <COMMAND> [COMMAND_OPTIONS] [ARGS]
```

**Phase 2 scope supports a single `scan` command implied by default:**

```
pyreach [OPTIONS] <PROJECT_PATH>
```

### 2.2 Options Reference

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--manifest` | `-m` | string | `requirements.txt` | Path to dependency manifest (relative to PROJECT_PATH) |
| `--db-path` | `-d` | string | `~/.pyreach/osv.db` | Path to OSV SQLite database |
| `--output` | `-o` | string | `pyreach-results.sarif` | Output file path |
| `--format` | `-f` | choice | `sarif` | Output format: `sarif`, `json`, `text` |
| `--entry-point` | `-e` | string (repeatable) | auto-detect | Fully qualified entry point(s) |
| `--max-depth` | `-k` | int | `5` | Max call graph traversal depth |
| `--include-potentially` | | flag | False | Treat POTENTIALLY_REACHABLE as failure |
| `--include-all` | | flag | False | Include NOT_REACHABLE results in output |
| `--no-fail` | | flag | False | Always exit 0 regardless of findings |
| `--cache` | | flag | True | Use call graph caching if available |
| `--exclude` | | string (repeatable) | [] | Path patterns to exclude from analysis |
| `--verbose` | `-v` | flag | False | Enable DEBUG logging |
| `--quiet` | `-q` | flag | False | Suppress all non-error output |
| `--version` | | flag | False | Show version and exit |
| `--help` | `-h` | flag | False | Show help message and exit |

### 2.3 Subcommand: `sync-osv` (Future / Sprint 1 Deliverable)

```
pyreach sync-osv [OPTIONS]
```

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--db-path` | `-d` | string | `~/.pyreach/osv.db` | Target SQLite database |
| `--source` | `-s` | string | `https://storage.googleapis.com/osv-vulnerabilities/index.html` | OSV export URL or local directory |
| `--incremental` | | flag | True | Only process records modified since last sync |

### 2.4 CLI Output Formats

#### `text` Format (Human-Readable)

```
PyReach v0.1.0 - Static Reachability Analysis
=============================================
Project: /home/user/projects/myapp
Manifest: requirements.txt
Entry points: main.app, api.routes.health_check
Max depth: 5

[1/3] Parsing dependencies... 15 packages found.
[2/3] Loading OSV advisories... 42 advisories match installed versions.
[3/3] Building call graph and analyzing reachability... Done in 12.3s.

Results Summary:
----------------
REACHABLE:              3
POTENTIALLY REACHABLE:  7
NOT REACHABLE:         32
TOTAL:                 42

Reachable CVEs:
  - CVE-2023-32681 (HIGH) in requests==2.31.0
    Path: main.app -> myapp.client.ApiClient.fetch_data -> requests.sessions.Session.request
    File: src/myapp/client.py:24

  - CVE-2023-YYYYY (MEDIUM) in urllib3==2.0.0
    Path: main.app -> myapp.client.ApiClient.fetch_data -> urllib3.connectionpool.HTTPConnectionPool._make_request
    File: src/myapp/client.py:25

Exit code: 1 (reachable vulnerabilities found)
```

#### `json` Format (Machine-Readable, Non-SARIF)

```json
{
  "tool": "PyReach",
  "version": "0.1.0",
  "project": "/home/user/projects/myapp",
  "summary": {
    "total": 42,
    "reachable": 3,
    "potentially_reachable": 7,
    "not_reachable": 32
  },
  "results": [
    {
      "vulnerability": {
        "cveId": "CVE-2023-32681",
        "packageName": "requests",
        "installedVersion": "2.31.0",
        "severity": "HIGH"
      },
      "status": "REACHABLE",
      "path": ["main.app", "myapp.client.ApiClient.fetch_data", "requests.sessions.Session.request"],
      "location": {
        "file": "src/myapp/client.py",
        "line": 24
      }
    }
  ]
}
```

### 2.5 Configuration File Precedence

Configuration values are resolved in the following priority (highest first):

1. CLI flags explicitly provided
2. `.pyreach.yml` in the project root
3. `~/.pyreach/config.yml` (user-global)
4. Built-in defaults

### 2.6 Progress Reporting

For interactive terminals, PyReach displays a simple progress indicator:

```
[1/4] Parsing manifest.................. DONE (0.2s)
[2/4] Loading advisories.............. DONE (1.1s)
[3/4] Building call graph............. DONE (8.4s)
[4/4] Analyzing reachability.......... DONE (2.6s)
```

In CI environments (`--quiet` or non-TTY), progress is suppressed and only the final summary is printed to stdout.

## 3. Error Messages and User Guidance

| Error Scenario | Message | Recommended Action |
|----------------|---------|-------------------|
| Missing manifest | `Error: Manifest file 'requirements.txt' not found in /path/to/project. Use --manifest to specify location.` | Check file path or create manifest |
| Missing OSV DB | `Error: OSV database not found at ~/.pyreach/osv.db. Run 'pyreach sync-osv' to download.` | Run sync command |
| No entry points | `Error: No entry points detected. Use -e to specify entry points explicitly.` | Add `-e` flags or `.pyreach.yml` config |
| Syntax error in source | `Warning: Skipping src/myapp/broken.py due to syntax error (line 15).` | Fix source file syntax |
| Out of memory | `Error: Memory limit exceeded during call graph construction. Try reducing --max-depth or excluding large packages.` | Reduce scope |
| Invalid SARIF schema (test only) | `AssertionError: SARIF output does not validate against OASIS schema.` | Report bug to maintainers |

---

*Document version: 1.0*
*Date: 2026-09-10*
*Status: Draft for Phase 2 Implementation*
