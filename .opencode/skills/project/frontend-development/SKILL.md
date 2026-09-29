---
name: frontend-development
description: Implement or refactor Fulbo React/Vite UI features, screens, hooks, and client-side state. Use for frontend work; not for defining backend endpoints or database changes.
---

# Fulbo frontend development

Work inside `frontend/`. The application is React 18 + Vite + TypeScript; `@` resolves to `frontend/src/app`.

## Structure and boundaries

- Prefer the existing feature folders, hooks, types, and shared UI primitives before adding a parallel pattern.
- Keep view concerns in screens/components and reusable state or domain behavior in hooks.
- Use `frontend/src/services/` for API access. Do not introduce ad-hoc `fetch` calls in components.
- Preserve player and manager flows independently when their authorization or data differs.

## API work

Treat existing client methods as contracts to verify, not proof that the server endpoint exists. For a new or changed endpoint, use the `api-integration` skill and coordinate DTO, response, error, and authorization behavior with the backend.

## Verification

Run `npm run build` from `frontend/` for implementation changes. Frontend test tooling is not configured; add a test runner and script before adding a production test suite.
