# linear_reachable

`main()` calls `client.fetch()`, which calls `vuln_lib.risky()`.

Expected verdict: **REACHABLE** via
`main.main -> client.fetch -> vuln_lib.risky`.
