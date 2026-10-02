# package_unused

`vuln_lib` is pinned as a dependency but is never imported by the application.
The vulnerable symbol `vuln_lib.risky` is therefore absent from the call graph.

Expected verdict: **NOT_REACHABLE** (package never imported).
