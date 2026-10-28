# Backend index

One FastAPI modular monolith. Verticals import platform `core`; `core` does not import verticals except the composition root (`core/src/main.py`) and Alembic. Verticals do not import each other.

| Path | What it is | Open when… |
| --- | --- | --- |
| [`core/`](core/) | Platform: IdentityAccess, Audit, ProcessTrace, EventBus, app factory | Auth, users, RBAC, traces |
| [`work/`](work/) | WorkManagement | Tasks, workflows |
| [`notify/`](notify/) | Notifications (inbox + webhooks) | Channels, deliveries, unread |
| `freight/` | *(not built yet)* | Shipments, tracking |
| `warehouse/` | *(not built yet)* | Locations, stock |

Run API and tests from **[`core/`](core/)** (`uv run uvicorn` / `uv run pytest`); `pythonpath` includes `../work/src` and `../notify/src`.
