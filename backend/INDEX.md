# Backend index

One FastAPI modular monolith. Each product slice lives under `backend/`.

| Path | What it is | Open when… |
| --- | --- | --- |
| [`core/`](core/) | IdentityAccess + WorkManagement (login, RBAC, open tasks, notify channels, inbox) | Auth, users, tasks, workflows, webhooks |
| `freight/` | *(not built yet)* | Shipments, tracking |
| `warehouse/` | *(not built yet)* | Locations, stock |

Removed from this product cut: CRM, Commercial, Trading, Finance.

Start here for this release: **[`core/INDEX.md`](core/INDEX.md)**.
