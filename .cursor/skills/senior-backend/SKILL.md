---
name: senior-backend
description: Senior backend engineering for the Karam Al Arab ERP. Use when designing or changing NestJS adapters, REST APIs, Prisma mapping, auth, jobs, or any apps/api infrastructure around DDD bounded contexts.
---

# Senior backend

Act as a senior backend engineer **implementing the DDD architecture**. Read `.cursor/skills/ddd-architecture/SKILL.md` first, then the domain skill and the cybersecurity skill before touching auth, money, or object ids.

Sources: [Microsoft REST API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design), [Twelve-Factor App](https://12factor.net/), NestJS as the HTTP adapter, Google eng practices.

## Architecture

DDD modular monolith. NestJS is the interface adapter, Prisma is infrastructure. Bounded context folders:

```
apps/api/src/
  shared-kernel/
  identity-access/
  crm/
  commercial/
  freight/
  warehouse/
  trading/
  finance/
  audit/
```

Each context: `domain/`, `application/`, `infrastructure/`, `interface/`. Domain imports neither Nest nor Prisma.

- Controllers adapt HTTP: auth, validate transport DTO, dispatch one application command, map the result.
- Application handlers load **one** aggregate, call a domain method, save, publish events.
- Other contexts are not called through their repositories. Use identity + events.
- No `forwardRef()` as a design tool. Cycles mean the bounded context is wrong.

## REST

- Nouns, plural collections: `GET /shipments`, `POST /shipments`, `GET /shipments/{id}`, `PATCH /shipments/{id}`.
- No `/create-shipment`. HTTP already has the verb.
- JSON + UTF-8. Meaningful status: `201` create, `204` empty delete, `400` validation, `401` unauthenticated, `403` forbidden, `404` missing or not authorized to know it exists, `409` conflict, `429` rate limit.
- Filter/sort/page with query params: `GET /shipments?status=in_transit&page=1&pageSize=25`.
- Keep URIs shallow: `/customers/{id}/shipments`, then `/shipments/{id}`. Not `/customers/1/orders/99/products`.
- Version only when a breaking change is unavoidable (`/v1`). Do not version on day one without a reason.

## Data

- PostgreSQL. Prisma migrations in source control.
- Money: `Decimal`. Quantities that can be fractional (kg, CBM) are decimal. Counts are integers.
- Soft-delete only when finance or audit needs the row. Otherwise hard delete inside a transaction with audit.
- Every mutating use case writes an audit row: actor, action, entity, before/after summary.
- Idempotency key on `POST /quotes` and `POST /shipments` so a double click does not double-book.

## Authn / authz

- Session or server-issued token. No secrets in the client bundle.
- Deny by default. Permission names are `{module}:{action}` (`shipments:update`).
- **Object-level checks on every id.** A user with `shipments:read` still cannot read another customer’s shipment.
- Never trust `X-User-Id` or `X-Forwarded-*` from the browser. If a proxy sets them, overwrite at the edge.
- Passwords hashed with a modern KDF (Argon2id or bcrypt cost ≥ 12). MFA is a later increment; design the user table so it can be added.

## Twelve-factor

- Config from environment. `.env.example` lists keys with empty values. Real secrets never committed.
- Backing services (Postgres, SMTP, object storage) are swappable by URL.
- Logs as structured JSON to stdout. Request id on every line.
- Processes are stateless. Uploads go to object storage, not the local disk of a web node.
- Admin tasks are one-off commands (`prisma migrate deploy`), not hidden HTTP routes.

## Validation and errors

- Validate transport at the interface (DTO). Reject unknown fields (blocks mass assignment).
- Enforce invariants on the aggregate. Status machines and money totals are domain methods, not `class-validator` alone.
- Do not leak stack traces. Map domain errors to the status codes above (`409` for illegal transitions).
- One aggregate per transaction. Money, stock, and status each live on their own root.

## Done

- Module has tests for the use case (happy path + forbidden id + validation).
- Migration is reversible or has an explicit expand/contract note.
- Cybersecurity checklist items for the touched endpoints are marked.

See [reference.md](reference.md) for status codes, pagination, and module template.
