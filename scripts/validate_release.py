"""Reproduce P9 evidence with synthetic oracles, real CLI subprocesses and denied networking."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import socket, sys
from pathlib import Path

def deny(*args, **kwargs):
    with Path(sys.argv[1]).open('a') as f:
        f.write('blocked network attempt\\n')
    raise OSError('Networking denied during validation')

socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.getaddrinfo = deny
from pyreach.cli import main
raise SystemExit(main(sys.argv[2:]))
"""


def advisory(identifier: str, package: str, symbol: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "modified": "2026-11-01T00:00:00Z",
        "summary": "Controlled synthetic fixture, not a real vulnerability",
        "affected": [
            {
                "package": {"ecosystem": "PyPI", "name": package},
                "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2"}]}],
                "ecosystem_specific": {"symbols": [symbol]},
            }
        ],
    }


def invoke(output: Path, *args: str) -> dict[str, Any]:
    started = time.perf_counter()
    process = subprocess.run(
        [sys.executable, "-c", BOOTSTRAP, str(output / "network-attempts.log"), *args],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=ROOT,
    )
    return {
        "arguments": list(args),
        "returncode": process.returncode,
        "seconds": time.perf_counter() - started,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def validate(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    for file in (output / "network-attempts.log",):
        file.unlink(missing_ok=True)
    data = output / "advisories.jsonl"
    data.write_text(json.dumps(advisory("SYNTH-REACH", "vuln-lib", "vuln_lib.risky")) + "\n")
    db = output / "osv.db"
    sync = invoke(output, "sync-osv", "--source", str(data), "-d", str(db))
    assert sync["returncode"] == 0, sync
    records = []
    expected = {
        "linear_reachable": "REACHABLE",
        "dynamic_import": "POTENTIALLY_REACHABLE",
        "depth_limit": "POTENTIALLY_REACHABLE",
        "transitive_unreachable": "NOT_REACHABLE",
        "package_unused": "NOT_REACHABLE",
    }
    for name, status in expected.items():
        project = output / name
        shutil.copytree(ROOT / "tests/fixtures/projects" / name, project, dirs_exist_ok=True)
        destination = output / f"{name}.json"
        run = invoke(
            output,
            str(project),
            "-d",
            str(db),
            "-f",
            "json",
            "-o",
            str(destination),
            "--include-all",
            "--include-potentially",
            "--no-cache",
        )
        document = json.loads(destination.read_text())
        actual = document["results"][0]["status"]
        run.update(
            {
                "case": name,
                "expected": status,
                "obtained": actual,
                "passed": actual == status
                and run["returncode"] == (0 if status == "NOT_REACHABLE" else 1),
            }
        )
        records.append(run)
    sarif = output / "reachable.sarif"
    run = invoke(
        output, str(output / "linear_reachable"), "-d", str(db), "-o", str(sarif), "--no-cache"
    )
    schema = json.loads((ROOT / "tests/fixtures/sarif-schema-2.1.0.json").read_text())
    jsonschema.validate(json.loads(sarif.read_text()), schema)
    run.update({"case": "sarif_schema", "passed": run["returncode"] == 1})
    records.append(run)
    for label, arguments, code in (
        ("help", ["--help"], 0),
        ("bad_depth", [str(output / "linear_reachable"), "-d", str(db), "-k", "8"], 2),
        (
            "no_fail",
            [
                str(output / "linear_reachable"),
                "-d",
                str(db),
                "--no-fail",
                "-o",
                str(output / "override.sarif"),
            ],
            0,
        ),
        ("missing_db", [str(output / "linear_reachable"), "-d", str(output / "missing.db")], 2),
    ):
        run = invoke(output, *arguments)
        run.update({"case": label, "expected_exit": code, "passed": run["returncode"] == code})
        records.append(run)
    corpus = output / "load_corpus"
    corpus.mkdir(exist_ok=True)
    manifest = ["vuln-lib==1.0.0", *[f"sample-{n}==1.0.0" for n in range(49)]]
    (corpus / "requirements.txt").write_text("\n".join(manifest) + "\n")
    (corpus / "main.py").write_text(
        "import vuln_lib\ndef main():\n    vuln_lib.risky()\n    vuln_lib.other()\n"
        "if __name__ == '__main__':\n    main()\n"
    )
    (corpus / "vuln_lib.py").write_text("def risky():\n    pass\ndef other():\n    pass\n")
    for n in range(100):
        (corpus / f"module_{n}.py").write_text(
            "\n".join(f"def function_{k}():\n    return {k}" for k in range(20))
        )
    controlled = [
        advisory("LOAD-R1", "vuln-lib", "vuln_lib.risky"),
        advisory("LOAD-R2", "vuln-lib", "vuln_lib.other"),
    ]
    controlled.extend(advisory(f"LOAD-N{n}", f"sample-{n}", f"sample_{n}.risky") for n in range(8))
    load_data = output / "load-advisories.jsonl"
    load_data.write_text("\n".join(json.dumps(x) for x in controlled) + "\n")
    load_db = output / "load-osv.db"
    assert (
        invoke(output, "sync-osv", "--source", str(load_data), "-d", str(load_db))["returncode"]
        == 0
    )

    def scan(index: int) -> dict[str, Any]:
        destination = output / f"load-{index}.json"
        run = invoke(
            output,
            str(corpus),
            "-d",
            str(load_db),
            "--no-cache",
            "--include-all",
            "-f",
            "json",
            "-o",
            str(destination),
        )
        run["summary"] = json.loads(destination.read_text())["summary"]
        return run

    serial = [scan(n) for n in range(3)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        concurrent_runs = list(pool.map(scan, range(3, 15)))
    timings = [x["seconds"] for x in concurrent_runs]
    load = {
        "direct_dependencies": 50,
        "source_files": 102,
        "declared_functions": 2003,
        "serial_runs": serial,
        "concurrent_workers": 4,
        "concurrent_runs": concurrent_runs,
        "p50_seconds": statistics.median(timings),
        "p95_seconds": sorted(timings)[-1],
        "p95_method": "nearest-rank ceil(0.95*N), N=12",
        "max_seconds": max(timings),
        "budget_seconds": 45,
        "all_within_budget": all(x <= 45 for x in timings),
        "controlled_reduction_percent": serial[0]["summary"]["reduction_percent"],
    }
    network_attempts = (
        (output / "network-attempts.log").read_text().splitlines()
        if (output / "network-attempts.log").exists()
        else []
    )
    document = {
        "date": "2026-11-04",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "fixture_notice": "Synthetic local fixtures; no Lidercom data or user acceptance implied",
        "cases": records,
        "load": load,
        "blocked_network_attempts": len(network_attempts),
        "passed": all(x["passed"] for x in records)
        and load["all_within_budget"]
        and not network_attempts,
    }
    (output / "results.json").write_text(json.dumps(document, indent=2))
    print(json.dumps({k: v for k, v in document.items() if k not in {"cases", "load"}}, indent=2))
    return document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("release-evidence"))
    args = parser.parse_args()
    result = validate(args.output.resolve())
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
