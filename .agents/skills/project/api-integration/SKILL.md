---
name: api-integration
description: Align Fulbo frontend service calls with NestJS REST endpoints, DTOs, authentication, error handling, and environment configuration. Use for cross-frontend/backend contract work.
---

# Fulbo API integration

Fulbo's frontend service layer is under `frontend/src/services/`. The NestJS backend serves `/api` and documents live endpoints at `/api/docs`.

## Contract-first workflow

- Define or confirm the backend request DTO, response shape, validation failures, authorization requirement, and status codes before changing the client.
- Update the frontend service method, types, and consuming hook/screen together. Do not duplicate backend types casually across unrelated features.
- Distinguish unavailable backend endpoints from failed requests. Prototype UI flows must not silently present unfinished operations as successful.
- Keep API base URLs in environment configuration; do not hardcode development URLs in feature components.

## High-risk flows

For authentication, phone verification, field availability, booking, and manager actions, test both successful and rejected paths. Confirm protected calls send the expected bearer token and that the server remains the authority for roles and ownership.

## Verification

Use Swagger or endpoint tests to verify the API contract, then run the backend checks and `npm run build` in `frontend/`.
