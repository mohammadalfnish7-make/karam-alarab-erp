# Backend index

One FastAPI modular monolith. Each product slice lives under `backend/`.

| Path | What it is | Open when… |
| --- | --- | --- |
| [`core/`](core/) | IdentityAccess: login, sessions, open RBAC, audit | Auth, users, roles, permissions, sessions |
| `crm/` | *(not built yet)* | Customers, contacts |
| `commercial/` | *(not built yet)* | Quotes, bookings |
| `freight/` | *(not built yet)* | Shipments, tracking |
| `warehouse/` | *(not built yet)* | Locations, stock |
| `trading/` | *(not built yet)* | SKUs, trading orders |
| `finance/` | *(not built yet)* | Invoices, claims |

Start here for this release: **[`core/INDEX.md`](core/INDEX.md)**.
