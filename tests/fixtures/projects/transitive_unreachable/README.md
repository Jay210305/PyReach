# transitive_unreachable

`main()` calls `safe_lib.safe()`, which transitively imports `vuln_lib` but
never calls `vuln_lib.risky()`.

Expected verdict: **NOT_REACHABLE** — the vulnerable symbol is present in the
dependency graph but sits on no call path from the entry point.
