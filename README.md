# Karam Al Arab ERP

Internal operations platform for **Karam Al Arab**, a Sharjah-based contract logistics and trading company. Public site: [karam-alarab.com](https://www.karam-alarab.com/).

After this platform ships, warehouse, freight, trading, finance, and support staff run the company in one system: customers, quotes, shipments, stock, invoices, and tracking — with English and Russian from day one.

This repository is the product source of truth. Backend lives under `backend/` (FastAPI); the first slice is `backend/core` (login + open RBAC). Frontend will live under `frontend/`. See [`backend/INDEX.md`](backend/INDEX.md). Agent skills, Cursor rules, and this README define how we design, build, test, and secure it.

## Company facts (from the live site)

Checked on 27 Oct 2026 against [karam-alarab.com](https://www.karam-alarab.com/), [About](https://www.karam-alarab.com/about-us), [Air freight](https://www.karam-alarab.com/service/air-freight), [Road freight](https://www.karam-alarab.com/service/road-freight), [Trading](https://www.karam-alarab.com/service/trading), [Book now](https://www.karam-alarab.com/book-now), and [Contact](https://www.karam-alarab.com/contact-us).

| Fact | Value |
| --- | --- |
| Legal / brand name | KARAM AL ARAB |
| Position | Contract logistics provider with 3PL warehousing and trading |
| HQ | Sharjah Industrial Area 11, United Arab Emirates |
| Phone | +971 58 304 2287 |
| Booking hours | Mo–Fr 08:30–17:30 (site also promises 24/7 shipment support) |
| Languages | English and Russian (`/ru`) |
| Markets | UAE, GCC, EU, CIS, Russia |
| Values | Excellence, innovation, transparency, customer-centricity, cargo security |
| Mission | Streamline international trade so success in the UAE, CIS, and Russia is achievable |

**Services to model in the ERP**

- **3PL warehousing** — end-to-end storage and supply-chain support
- **Air freight** — urgent, high-value, fragile, temperature-sensitive cargo; tracking and cargo updates
- **Road freight** — FTL, LTL, box, flatbed, refrigerated; door-to-door across UAE, GCC, EU, CIS
- **Trading** — auto spare parts, perfumes, cosmetics, hygiene products, cleaning supplies
- **Financial protection** — compensation claims when cargo is damaged or lost
- **Book now** — goods type (example: cosmetics), weekly vs monthly cadence, callback

The marketing homepage still contains leftover “Talal Logistics” copy. Do not reuse that name in product UI, emails, or invoices.

## What agents must do

Every implementation, review, or test in this repo loads the matching senior skill. Do not improvise a junior stack.

| Work | Skill | Rule |
| --- | --- | --- |
| Company language, users, money, locales | `.cursor/skills/karam-alarab-domain/` | always |
| Bounded contexts, aggregates, domain events | `.cursor/skills/ddd-architecture/` | `ddd.mdc` (always) |
| Decided runtimes (FastAPI + React) | `.cursor/skills/tech-stack/` | `stack.mdc` (always) |
| UI code, React, Vite, TypeScript | `.cursor/skills/senior-frontend/` | `frontend.mdc` |
| APIs, FastAPI adapters, SQLAlchemy mapping | `.cursor/skills/senior-backend/` | `backend.mdc` |
| Layout, brand, accessibility, workflows | `.cursor/skills/senior-ui-ux/` | `ui-ux.mdc` |
| Manual cases and Playwright | `.cursor/skills/senior-qa/` | `qa.mdc` |
| Threat model, OWASP, ASVS checks | `.cursor/skills/senior-cybersecurity/` | `cybersecurity.mdc` |

Entry point for agents: [AGENTS.md](AGENTS.md).

## Outcome, scope, and sequence

### Outcome

Ops staff in Sharjah can create a customer, quote a shipment or trading order, move stock, update tracking, and raise an invoice without spreadsheets.

### In scope (platform foundation, then first vertical)

1. Identity, RBAC, audit log
2. Customers and contacts
3. Quotes and bookings (air / road / trading)
4. Shipments and tracking status
5. Warehouse locations and stock for traded goods and 3PL goods
6. Invoices and compensation claims
7. English + Russian UI, AED money, Asia/Dubai time

### Out of scope until someone asks

- Public marketing site rewrite
- Customer self-serve portal (tracking is internal first)
- Sea-freight module as a first-class mode (mentioned on the blog, not a nav service)
- Arabic UI (prepare layout for RTL; do not ship AR copy yet)
- Multi-company tenancy (this is one company)
- Native mobile apps

### Architecture (decided)

**Domain-Driven Design modular monolith.** Not table-CRUD, not microservices.

Eight bounded contexts in one FastAPI process and one PostgreSQL database: IdentityAccess, CRM, Commercial, Freight, Warehouse, Trading, Finance, Audit. Each context owns its tables and aggregates. Contexts collaborate by identity (`CustomerId`, `ShipmentId`) and domain/integration events. One aggregate per transaction. Domain code has no FastAPI, Pydantic, or SQLAlchemy imports.

Details: `.cursor/skills/ddd-architecture/`.

### Stack (decided)

- `backend/core` — latest stable Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL
- `frontend/` — latest stable React, TypeScript, Vite, React Router, TanStack Query, Tailwind (Node LTS) — not in this slice yet
- Contract — FastAPI OpenAPI; React generates TS types from it
- Tests — latest stable pytest and Playwright
- Versions — re-check PyPI/npm before every install; snapshot in `.cursor/skills/tech-stack/versions.md`
- Deploy later as a Python API + static React (confirm host before first production push)

DDD stays if the host changes. Do not add NestJS, Next.js, or Prisma.

### Sequence

1. DDD skeleton — shared kernel, IdentityAccess login + open RBAC **(in tree under `backend/core`)** — see [`backend/core/INDEX.md`](backend/core/INDEX.md)
2. CRM + Commercial — a cosmetics weekly quote can be stored
3. Freight — air or road shipment status is visible
4. Warehouse — receive and pick trading SKUs
5. Finance — invoice and claim post only through aggregate commands
6. i18n RU parity and Playwright critical paths on CI

Each step must be reversible and demoable on its own.

### Run locally

Default API database is SQLite (`backend/core/var/karam.db`) so IdentityAccess can be demoed without Docker. PostgreSQL 18 is required when `ENVIRONMENT=production`; `docker compose up db` then set `DATABASE_URL`.

```bash
# API (core)
cd backend/core
cp .env.example .env
# Set ENVIRONMENT=development, SEED_ADMIN_PASSWORD (12+ chars), WEB_ORIGIN=http://127.0.0.1:5173
uv sync
uv run uvicorn main:app --app-dir src --reload --port 8000
```

API health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health). Login: `POST /sessions` with `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`.

Web UI is not in this slice yet.

```bash
cd backend/core && uv run pytest
```

### Risks

- Copying the marketing site into the ERP — impact: unusable ops UI — mitigation: dense enterprise layouts, brand tokens only
- Floating-point money or UTC-only timestamps — impact: accounting and customs errors — mitigation: decimal money, store UTC, display Dubai
- Object-level authorization gaps on shipment/invoice IDs — impact: data leak between customers — mitigation: senior cybersecurity skill on every endpoint
- Building sea, fleet, and portal before quotes work — impact: no operational value — mitigation: sequence above

### Decisions needed

- Confirm whether warehouse is bonded / free-zone (affects Warehouse aggregates)
- Confirm who the first live users are (ops, sales, warehouse)

## Brand (extracted from the live site)

| Token | Value |
| --- | --- |
| Primary | `#1769FF` |
| Text | `#212529` |
| Muted | `#767474` |
| Wash | `rgba(148, 192, 255, 0.18)` |
| White | `#FFFFFF` |
| Font | Montserrat, system-ui, sans-serif |

Use these colors in the ERP chrome. Do not clone the sparse marketing homepage. Ops users need tables, filters, status, and keyboard speed. Details: `.cursor/skills/senior-ui-ux/brand.md`.

## Domain language

Prefer the words the company already uses:

shipment, cargo, consignment, 3PL, FTL, LTL, air freight, road freight, trading, auto spare parts, perfumes, cosmetics, hygiene, cleaning supplies, tracking, compensation, door-to-door, refrigerated, Sharjah, AED.

Do not invent SAP-style jargon (plant, sto, vbdk) unless a user asks for it.

## Sources the skills are based on

- [React — Thinking in React](https://react.dev/learn/thinking-in-react)
- [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html)
- [Google Engineering Practices](https://google.github.io/eng-practices/)
- [Microsoft REST API design](https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design)
- [Twelve-Factor App](https://12factor.net/)
- [Nielsen Norman Group — 10 usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
- [NNG — heuristics for complex applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Playwright best practices](https://playwright.dev/docs/best-practices)
- [Kent C. Dodds — Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [OWASP Top 10:2025](https://owasp.org/Top10/2025/)
- [OWASP API Security Top 10:2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/)
- [OWASP ASVS 5.0](https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release)
- [Microsoft tactical DDD](https://learn.microsoft.com/en-us/azure/architecture/microservices/model/tactical-domain-driven-design)
- [Vernon — Effective Aggregate Design](https://kalele.io/wp-content/uploads/2019/01/DDD_COMMUNITY_ESSAY_AGGREGATES_PART_2.pdf)
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Vite](https://vite.dev/guide/)
