# Core index — login + open permissions

Everything for IdentityAccess lives under `backend/core`. Go to the folder that matches the problem; do not hunt across the tree.

## Folder map

| Folder | Contains | Open when… |
| --- | --- | --- |
| [`src/main.py`](src/main.py) | App factory, CORS, middleware, router mount | Boot / wiring |
| [`src/config/`](src/config/) | Env settings (`Settings`) | `.env`, DATABASE_URL, seed admin, cookies |
| [`src/database/`](src/database/) | **All persistence** | SQL, tables, seed, repos |
| [`src/database/engine.py`](src/database/engine.py) | SQLAlchemy engine + `Base` | Connection / SQLite vs Postgres |
| [`src/database/models/`](src/database/models/) | Table definitions only | Schema / columns / indexes |
| [`src/database/repositories/`](src/database/repositories/) | Load/save adapters | Queries, “why didn’t it save?” |
| [`src/database/password.py`](src/database/password.py) | Argon2 hash/verify | Password hashing |
| [`src/database/seed.py`](src/database/seed.py) | Roles, permissions, seed admin | First login / empty DB |
| [`src/domain/`](src/domain/) | Pure rules (no FastAPI/SQLAlchemy) | Business invariant bugs |
| [`src/domain/shared/`](src/domain/shared/) | `UserId`, errors, events, clock | Shared types |
| [`src/domain/identity/`](src/domain/identity/) | User aggregate, permissions format, ports | Last-admin, role rules |
| [`src/application/`](src/application/) | Use cases / services | Login flow, create user, audit listener |
| [`src/api/`](src/api/) | HTTP: routers, DTOs, deps, error envelope | Status codes, routes, cookies |
| [`src/support/`](src/support/) | Event bus, JSON logging | Events after commit, request logs |
| [`alembic/`](alembic/) | Migrations | Schema history |
| [`tests/`](tests/) | Pytest | Regressions |
| [`var/`](var/) | Local SQLite file (gitignored `*.db`) | Local demo DB |

## HTTP surface (auth)

| Method | Path | File |
| --- | --- | --- |
| GET | `/health` | `src/main.py` |
| POST | `/sessions` | `src/api/session_router.py` |
| DELETE | `/sessions/current` | `src/api/session_router.py` |
| GET/PATCH | `/users/me`, `/users/me/password` | `src/api/user_router.py` |
| GET/POST/PATCH | `/users`, `/users/{id}` | `src/api/user_router.py` |
| GET | `/roles`, `/permissions` | `src/api/user_router.py` |
| PUT | `/roles/{name}/permissions` | `src/api/user_router.py` |
| POST | `/permissions/register` | `src/api/user_router.py` |

## Run

```bash
cd backend/core
cp .env.example .env   # set SEED_ADMIN_PASSWORD (12+)
uv sync
uv run uvicorn main:app --app-dir src --reload --port 8000
uv run pytest
```
