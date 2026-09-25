---
name: backend-api-development
description: Build or modify Fulbo NestJS API modules, endpoints, DTOs, guards, and services. Use for backend behavior; pair with prisma-migrations when persistence changes.
---

# Fulbo backend API development

Work inside `backend/`. The API is NestJS with ESM TypeScript, uses the `/api` prefix, and exposes Swagger at `/api/docs`.

## Module conventions

- Follow the established `AuthModule`, `PrismaModule`, shared guards, decorators, and exception filter rather than bypassing them.
- Keep controllers thin; put business rules and persistence orchestration in services.
- Use DTOs with `class-validator` for request input. The global validation pipe whitelists and rejects unknown fields.
- Preserve `.js` import specifiers in TypeScript source, matching the current ESM configuration.

## Authorization and domain rules

JWT and role guards are global. Mark only intentionally unauthenticated routes public. Enforce owner/resource authorization in the service or guard layer, not only in the frontend.

For booking, schedule, or payment-state work, make conflict and transition rules explicit and test them. Use `prisma-migrations` for schema changes and `api-integration` when a frontend contract changes.

## Verification

Run the smallest relevant checks from `backend/`: `npm run build`, `npm run lint`, `npm test`, and/or `npm run test:e2e`.
