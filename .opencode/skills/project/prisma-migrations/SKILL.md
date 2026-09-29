---
name: prisma-migrations
description: Safely evolve Fulbo's PostgreSQL Prisma schema, migrations, seed data, and generated client. Use whenever persistent models, relations, indexes, or database constraints change.
---

# Fulbo Prisma migrations

The PostgreSQL schema lives at `backend/prisma/schema.prisma`; Prisma 7 configuration is in `backend/prisma.config.ts`. The generated client is written under `backend/src/generated/` and is not committed.

## Change discipline

- Model relationships, required fields, indexes, and deletion behavior deliberately. Booking availability and ownership are integrity-sensitive.
- Make every schema change through a reviewed migration; do not rely on a generated client alone.
- Keep seed data compatible with the schema when the change affects local development.
- Check whether existing data needs a backfill or a safe staged migration before adding a required constraint.

## Verification

Generate and validate Prisma after schema work, apply the migration to a disposable local database, and run tests that exercise affected business rules. Never commit `.env` files or generated client output.
