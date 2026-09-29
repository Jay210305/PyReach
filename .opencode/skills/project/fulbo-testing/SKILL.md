---
name: fulbo-testing
description: Add or improve automated verification for Fulbo backend, frontend, and cross-application workflows. Use when writing tests, choosing coverage, or validating risky changes.
---

# Fulbo testing

The backend uses Vitest and Supertest. Current scripts and legacy suites use `backend/test/` (singular); `backend/tests/` is the preferred destination only after Vitest, lint, and formatting globs are updated together. The frontend has no configured test runner yet.

## Priorities

- Backend: authentication and role checks, ownership boundaries, phone verification, booking conflict detection, schedule overlap, and state transitions.
- Integration: API validation errors, token handling, and frontend behavior for loading, empty, and rejected states.
- Frontend: configure a runner and npm script before adding tests; focus first on behavior rather than implementation details.

## Test design

Use a disposable database for endpoint tests that persist data. Assert observable contracts—status, body, authorization, and persisted outcome. Avoid tests dependent on external SMS, payments, Cloudinary, or realtime services; inject or mock their boundaries.

## Verification

Run the relevant existing scripts from `backend/`. Report any test that cannot run because its runner, database, or environment configuration is not yet available.
