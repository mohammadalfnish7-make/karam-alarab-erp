# Core index — IdentityAccess + WorkManagement

Everything for login/RBAC and the open task engine lives under `backend/core`.

## Folder map

| Folder | Contains | Open when… |
| --- | --- | --- |
| [`src/main.py`](src/main.py) | App factory, CORS, middleware, router mount | Boot / wiring |
| [`src/config/`](src/config/) | Env settings (`Settings`) | `.env`, DATABASE_URL, seed admin, cookies, uploads |
| [`src/database/`](src/database/) | **All persistence** | SQL, tables, seed, repos |
| [`src/domain/identity/`](src/domain/identity/) | User aggregate, permissions | Last-admin, role rules |
| [`src/domain/work/`](src/domain/work/) | Task engine + webhook signing/SSRF rules | Task invariants, notify crypto |
| [`src/application/`](src/application/) | Use cases / notify listener / delivery worker | Login, tasks, channels, fan-out |
| [`src/support/tracing.py`](src/support/tracing.py) | **Core ProcessTrace** recorder (all contexts) | Mid-process failures, correlation |
| [`src/api/`](src/api/) | HTTP routers + DTOs | Status codes, routes |
| [`alembic/`](alembic/) | Migrations (`0001` identity, `0002` work, `0003` traces) | Schema history |
| [`tests/`](tests/) | Pytest | Regressions |

## HTTP surface

### Auth

| Method | Path |
| --- | --- |
| GET | `/health` |
| POST/DELETE | `/sessions`, `/sessions/current` |
| GET/PATCH | `/users/me`, `/users/me/password` |
| GET/POST/PATCH | `/users`, `/users/{id}` |
| GET/PUT/POST | `/roles`, `/permissions`, … |

### Work

| Method | Path |
| --- | --- |
| POST/GET | `/workflows`, `/workflows/{id}` |
| POST/GET/PATCH | `/task-types` |
| POST/GET | `/tasks`, `/tasks/{id}` |
| POST/PATCH | `/tasks/{id}/transitions`, `/assignee`, `/steps`, `/comments`, `/attachments`, `/entity-links`, `/links` |
| POST/GET/PATCH/DELETE | `/notification-channels` (+ `/roll-secret`) |
| GET/POST | `/notifications`, `/unread-count`, `/{id}/read`, `/read-all` |
| POST | `/work/process-deliveries` (dev/test only) |

### Process traces (core, all contexts)

| Method | Path |
| --- | --- |
| GET | `/process-traces` |
| GET | `/process-traces/{id}` |
| GET | `/process-traces/by-correlation/{correlationId}` |

Permission: `process:read`. Future Freight/Warehouse call the same `TraceRecorder` — do not add per-module trace tables.

Task types and channels start **empty** — admin creates them. Assign enqueues inbox + webhook deliveries; `POST /work/process-deliveries` (or `process_pending_deliveries`) POSTs webhooks.

## Run

```bash
cd backend/core
cp .env.example .env   # set SEED_ADMIN_PASSWORD (12+)
uv sync
uv run uvicorn main:app --app-dir src --reload --port 8000
uv run pytest
```
