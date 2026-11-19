# depth_limit

`main()` reaches `vuln_lib.risky()` through a purely static chain of length 6:

`main.main -> chain.a -> chain.b -> chain.c -> chain.d -> chain.e -> vuln_lib.risky`

With `max_depth=5`, the target is one hop beyond the bound.

Expected verdict: **NOT_REACHABLE** (depth limit, no dynamic edge).
