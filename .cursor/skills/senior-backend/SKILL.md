---
name: senior-backend
description: Senior backend engineering for the Karam Al Arab ERP. Use when designing or changing FastAPI routers, Pydantic DTOs, SQLAlchemy mapping, Alembic migrations, auth, jobs, or any backend/ infrastructure around DDD bounded contexts.
---

# Senior backend

Act as a senior backend engineer **implementing the DDD architecture on FastAPI**. Read `.cursor/skills/ddd-architecture/SKILL.md` and `.cursor/skills/tech-stack/SKILL.md` first, then the domain skill and the cybersecurity skill before touching auth, money, or object ids.

Sources: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://docs.sqlalchemy.org/), [Microsoft REST API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design), [Twelve-Factor App](https://12factor.net/). Use the latest stable versions from `.cursor/skills/tech-stack/versions.md`.

## Architecture

DDD modular monolith. FastAPI is the interface adapter. SQLAlchemy is infrastructure. Bounded context packages:

```
backend/core/src/          # first slice (IdentityAccess) — see backend/core/INDEX.md
  main.py
  config/
  database/                # all SQLAlchemy models + repositories
  domain/shared/
  domain/identity/
  application/
  api/
  support/
```

Later bounded contexts add folders under `backend/` (e.g. `backend/freight/`). Inside a slice, keep domain free of FastAPI, Pydantic, and SQLAlchemy. Persistence code stays under that slice’s `database/` folder.

- Routers adapt HTTP: auth, validate Pydantic DTO (`extra="forbid"`), dispatch one application command, map the result.
- Application handlers load **one** aggregate, call a domain method, save, publish events.
- Other contexts are not called through their repositories. Use identity + events.
- Composition root is `main.py` plus each context’s FastAPI `APIRouter`. Cycles mean the bounded context is wrong.

## REST

- Nouns, plural collections: `GET /shipments`, `POST /shipments`, `GET /shipments/{id}`, `PATCH /shipments/{id}`.
- No `/create-shipment`. HTTP already has the verb.
- JSON + UTF-8. Meaningful status: `201` create, `204` empty delete, `400` validation, `401` unauthenticated, `403` forbidden, `404` missing or not authorized to know it exists, `409` conflict, `429` rate limit.
- Filter/sort/page with query params: `GET /shipments?status=in_transit&page=1&pageSize=25`.
- Keep URIs shallow: `/customers/{id}/shipments`, then `/shipments/{id}`. Not `/customers/1/orders/99/products`.
- Version only when a breaking change is unavoidable (`/v1`). Do not version on day one without a reason.
- OpenAPI from FastAPI is the contract the React app generates types from. Keep operation ids stable.

## Data

- PostgreSQL (latest stable major). Alembic migrations in source control.
- Money: `decimal.Decimal`. Quantities that can be fractional (kg, CBM) are decimal. Counts are integers.
- Soft-delete only when finance or audit needs the row. Otherwise hard delete inside a transaction with audit.
- Every mutating use case writes an audit row: actor, action, entity, before/after summary.
- Idempotency key on `POST /quotes` and `POST /shipments` so a double click does not double-book.

## Authn / authz

- Session or server-issued token in an HttpOnly cookie. No secrets in the client bundle.
- Deny by default. Permission names are `{context}:{action}` (`freight:update`).
- **Object-level checks on every id.** A user with `freight:read` still cannot read another customer’s shipment.
- Never trust `X-User-Id` or `X-Forwarded-*` from the browser. If a proxy sets them, overwrite at the edge.
- Passwords hashed with Argon2. MFA is a later increment; design the user table so it can be added.

## Twelve-factor

- Config from environment. `.env.example` lists keys with empty values. Real secrets never committed.
- Backing services (Postgres, SMTP, object storage) are swappable by URL.
- Logs as structured JSON to stdout. Request id on every line.
- Processes are stateless. Uploads go to object storage, not the local disk of a web node.
- Admin tasks are one-off commands (`cd backend/core && uv run alembic -c ../alembic.ini upgrade head`), not hidden HTTP routes. Migrations live in `backend/alembic/` (host infrastructure), not inside a context package.

## Validation and errors

- Validate transport at the interface (Pydantic). Reject unknown fields.
- Enforce invariants on the aggregate. Status machines and money totals are domain methods, not Pydantic validators alone.
- Do not leak stack traces. Map domain errors to the status codes above (`409` for illegal transitions).
- One aggregate per transaction. Money, stock, and status each live on their own root.

## Done

- Context has pytest for the use case (happy path + forbidden id + validation).
- Migration is reversible or has an explicit expand/contract note.
- Cybersecurity checklist items for the touched endpoints are marked.

See [reference.md](reference.md) for status codes, pagination, and context template.
