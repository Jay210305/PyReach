# Local scan targets

`Lidercom_Recoleccion/Backend/App/` is a local Python adaptation of the backend from the sibling `Lidercom_Recoleccion` repository. Its Rust extension was replaced with Python code while keeping the account service interface and stored credential format. The adaptation is excluded from Git; the original application stays in its own repository.

From the PyReach root, scan the copy with a populated local OSV database:

```powershell
uv run pyreach scan-targets/Lidercom_Recoleccion/Backend/App --db-path C:\path\to\osv.db --entry-point graphql.server --exclude Test/ --format sarif --output lidercom-results.sarif
```

The copied `requirements.txt` still has unpinned application dependencies, so its findings cannot establish which installed versions are affected. Use an environment-specific pinned `requirements.txt` before treating a result as a vulnerability assessment. PyReach also needs a populated OSV database; an empty database only checks that the scan command runs. The copied wallet implementation and its dependencies are tested with Python 3.13.

## PyReach validation

`Lidercom_Recoleccion/pyreach-demo-synthetic.sarif` is a local demonstration report generated with a temporary, **synthetic** advisory (`PYREACH-DEMO-NOT-REAL`) for `argon2-cffi==25.1.0`. It is not evidence of a real vulnerability. With `UserAccountService.create` supplied as the entry point, PyReach returned exit code 1 and reported one `REACHABLE` result. Its call flow is `UserAccountService.create` → `rust_services.register` → `rust_services._derive_key` → `argon2.low_level.hash_secret_raw`. The actual GraphQL server entry point does not statically expose that framework-mediated route to PyReach's call graph, so the service method was supplied explicitly for this test.

## Translation checklist

- [x] Recreate the backend under `scan-targets/` without modifying the original repository.
- [x] Replace the copied Rust extension with Python while preserving its account and login API.
- [x] Verify credential storage and wallet recovery with 44 passing tests.
- [x] Confirm PyReach's call graph resolves account creation and login into the Python module.
- [x] Run an end-to-end PyReach CLI scan against the copy and inspect its SARIF flow.
