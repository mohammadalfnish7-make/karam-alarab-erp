# Backend index

One FastAPI modular monolith (Clean Architecture: domain inward, DB/migrations outward). Verticals import platform `core`; `core` does not import verticals except the composition root (`core/src/main.py`). Verticals do not import each other.

| Path | What it is | Open when… |
| --- | --- | --- |
| [`alembic/`](alembic/) + [`alembic.ini`](alembic.ini) | Host schema history (one DB) | Migrations |
| [`core/`](core/) | Platform: IdentityAccess, Audit, ProcessTrace, EventBus, app factory | Auth, users, RBAC, traces |
| [`work/`](work/) | WorkManagement | Tasks, workflows |
| [`notify/`](notify/) | Notifications (inbox + webhooks) | Channels, deliveries, unread |
| `freight/` | *(not built yet)* | Shipments, tracking |
| `warehouse/` | *(not built yet)* | Locations, stock |

```bash
cd backend/core && uv run pytest
cd backend/core && uv run alembic -c ../alembic.ini upgrade head
```
