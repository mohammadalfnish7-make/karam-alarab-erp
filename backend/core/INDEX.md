# Core index — platform (IdentityAccess + Audit + ProcessTrace)

Login/RBAC, audit, shared EventBus/TraceRecorder, and the composition root that mounts vertical routers.

Verticals: **[`../work/`](../work/)** (tasks), **[`../notify/`](../notify/)** (inbox/webhooks). Do not add those back here.

## Folder map

| Folder | Contains | Open when… |
| --- | --- | --- |
| [`src/main.py`](src/main.py) | App factory (composition root; may import `work`) | Boot / wiring |
| [`src/config/`](src/config/) | Env settings (`Settings`) | `.env`, DATABASE_URL, seed admin, cookies, uploads |
| [`src/database/`](src/database/) | Platform persistence + seed | identity, audit, traces |
| [`src/domain/identity/`](src/domain/identity/) | User aggregate, permissions | Last-admin, role rules |
| [`src/domain/shared/`](src/domain/shared/) | Shared kernel (errors, events, ids) | Cross-context types |
| [`src/application/`](src/application/) | Auth, users, AuditListener | Login, RBAC |
| [`src/support/`](src/support/) | EventBus, TraceRecorder, logging | Mid-process failures, correlation |
| [`src/api/`](src/api/) | Session/user/trace routers + deps/errors | Status codes, routes |
| [`tests/`](tests/) | Platform + architecture boundary tests | Regressions |

Migrations live at the host: [`../alembic/`](../alembic/) (not inside IdentityAccess — Clean Architecture: DB is a detail).

## HTTP surface

### Auth

| Method | Path |
| --- | --- |
| GET | `/health` |
| POST/DELETE | `/sessions`, `/sessions/current` |
| GET/PATCH | `/users/me`, `/users/me/password` |
| GET/POST/PATCH | `/users`, `/users/{id}` |
| GET/PUT/POST | `/roles`, `/permissions`, … |

### Work (mounted from `backend/work`)

| Method | Path |
| --- | --- |
| POST/GET | `/workflows`, `/workflows/{id}` |
| POST/GET/PATCH | `/task-types` |
| POST/GET | `/tasks`, `/tasks/{id}` |
| POST/PATCH | `/tasks/{id}/transitions`, `/assignee`, `/steps`, `/comments`, `/attachments`, `/entity-links`, `/links` |

### Notify (mounted from `backend/notify`)

| Method | Path |
| --- | --- |
| POST/GET/PATCH/DELETE | `/notification-channels` (+ `/roll-secret`) |
| GET/POST | `/notifications`, `/unread-count`, `/{id}/read`, `/read-all` |
| POST | `/work/process-deliveries` (dev/test only; path kept) |

### Process traces (core, all contexts)

| Method | Path |
| --- | --- |
| GET | `/process-traces` |
| GET | `/process-traces/{id}` |
| GET | `/process-traces/by-correlation/{correlationId}` |

Permission: `process:read`. Future Freight/Warehouse call the same `TraceRecorder` — do not add per-module trace tables.

## Run

```bash
cd backend/core
cp .env.example .env   # set SEED_ADMIN_PASSWORD (12+)
uv sync
uv run uvicorn main:app --app-dir src --reload --port 8000
uv run pytest

# Schema (host alembic next to core/):
uv run alembic -c ../alembic.ini upgrade head
```
