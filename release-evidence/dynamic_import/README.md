# dynamic_import

`main()` loads a plugin with `importlib.import_module("vuln_lib")`, a dynamic
pattern that could reach `vuln_lib.risky()` at runtime.

Expected verdict: **POTENTIALLY_REACHABLE** — a `DYNAMIC` edge is on the path.
