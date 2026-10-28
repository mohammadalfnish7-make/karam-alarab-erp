---
name: tech-stack
description: Decided runtime stack and latest-stable version policy for the Karam Al Arab ERP. Use when scaffolding, adding dependencies, or choosing libraries. Backend is FastAPI (Python). Frontend is React (TypeScript SPA). Always install the current stable registry version, never RC/beta.
---

# Tech stack

Second architecture decision, after DDD: **FastAPI backend + React frontend**. DDD bounded contexts stay.

**Always the last stable version.** Before adding or bumping a dependency, query the registry. Prefer what is on PyPI/npm `latest` today over the snapshot in [versions.md](versions.md). Never install pre-release, RC, beta, `next`, or yanked packages.

Sources: [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy](https://docs.sqlalchemy.org/), [React](https://react.dev/), [Vite](https://vite.dev/guide/).

## Version policy

1. Runtimes: newest **stable** from the vendor. Python.org current (not 3.16 pre). Node **LTS** (not Current). PostgreSQL current major with latest minor (not beta/RC).
2. Libraries: `pip`/`uv` and `npm` **latest** tag, not yanked, no `a`/`b`/`rc` in the version.
3. Pin exact versions in lockfiles (`uv.lock`, `package-lock.json`). Manifests may use `>=` the current stable.
4. After install, if [versions.md](versions.md) is behind, update that snapshot.
5. If the newest stable cannot be used (incompatible peer, missing Python 3.15 wheel), take the newest that works and write the reason next to the pin.

Checked snapshot (27 Oct 2026): Python **3.15.2**, FastAPI **0.162.0**, SQLAlchemy **2.1.6**, React **19.3.1**, Vite **8.3.5**, Node **24.22.1 LTS**, PostgreSQL **18.6**. Full table: [versions.md](versions.md).

## Backend (`backend/core` first; later slices under `backend/`)

| Choice | Use |
| --- | --- |
| Language | Latest stable CPython (3.15.x) |
| HTTP | Latest stable FastAPI + Uvicorn |
| Transport DTOs | Latest stable Pydantic v2 in `interface/` only (`extra="forbid"`) |
| ORM / SQL | Latest stable SQLAlchemy 2.x mapped tables in `infrastructure/` |
| Migrations | Latest stable Alembic |
| Database | Latest stable PostgreSQL major (18.x); driver latest `psycopg` |
| Money | `decimal.Decimal` |
| Auth | HttpOnly cookie; latest `argon2-cffi` |
| Tests / lint | Latest pytest, latest Ruff |
| Package | `uv` lockfile committed |

FastAPI routers are the interface adapter. They must not contain status machines or money rules.

Do not use Django ORM, SQLModel as the domain model, or Pydantic models as aggregates.

## Frontend (`frontend/`; legacy path `apps/web` if present)

| Choice | Use |
| --- | --- |
| Runtime | Node.js **LTS** (24.x Krypton) |
| UI | Latest stable React + matching `react-dom` + TypeScript |
| Bundler | Latest stable Vite |
| Routing | Latest stable React Router, locale in path (`/en/shipments`) |
| Server state | Latest stable TanStack Query |
| Styling | Latest stable Tailwind + shadcn/ui |
| i18n | Latest stable i18next + react-i18next |
| API types | Generate from FastAPI OpenAPI |
| Tests | Latest stable `@playwright/test` |

Signed-in SPA talking to FastAPI over REST. No Next.js. Do not import Python domain into the browser.

## Contract

- REST JSON as in the backend skill.
- OpenAPI is the source of truth between FastAPI and React.
- Shared kernel lives in Python. The web app formats AED and Dubai time to match.

## Layout

```
backend/
  INDEX.md                 # map of backend slices
  alembic.ini + alembic/   # host migrations (Clean Architecture: DB is a detail)
  core/                    # platform: IdentityAccess, audit, traces — see core/INDEX.md
    src/
      main.py              # composition root (mounts vertical routers)
      config/              # settings
      database/            # engine, platform models/, repositories/, seed
      domain/              # shared/ + identity/ (no framework imports)
      application/         # auth, users, audit listener
      api/                 # session/user/trace routers, deps, errors
      support/             # event bus, TraceRecorder, logging
    tests/
  work/                    # WorkManagement — see work/INDEX.md
    src/work/{domain,application,api,database}/
    tests/
  notify/                  # Notifications — see notify/INDEX.md
    src/notify/{domain,application,api,database}/
  # later: freight/, warehouse/
frontend/                  # Vite + React (not in core slice yet)
```

## Explicitly not the stack

NestJS, Next.js, Prisma, Django, Flask as the app framework, Create React App, Node Current instead of LTS, PostgreSQL 19 RC, Python pre-releases.

## Done

- New packages are the current stable from the registry, lockfile pinned
- [versions.md](versions.md) matches or is updated
- Domain stays plain Python
