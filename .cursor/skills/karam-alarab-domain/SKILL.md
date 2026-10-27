---
name: karam-alarab-domain
description: Company domain, users, modules, money, locales, and language for the Karam Al Arab logistics and trading ERP. Use on every task in this repository, including planning, UI copy, schema, APIs, and tests.
---

# Karam Al Arab domain

Internal ERP for one company: Karam Al Arab, Sharjah Industrial Area 11, UAE. Public facts live on [karam-alarab.com](https://www.karam-alarab.com/). This skill is the product dictionary. Other skills assume it.

## Who uses it

| Role | Job | Default access |
| --- | --- | --- |
| Sales | Quotes, bookings, customers | customers, quotes |
| Operations | Air/road shipments, tracking, exceptions | shipments |
| Warehouse | Receive, put-away, pick, 3PL stock | warehouse |
| Trading | SKUs, suppliers, sales of parts/cosmetics | catalog, orders |
| Finance | Invoices, compensation claims | invoices, claims |
| Support | 24/7 status answers | shipments read |
| Admin | Users, roles, audit | all |

Do not invent extra personas. A person can hold more than one role.

## Bounded contexts (build in this order)

These are DDD contexts, not CRUD modules. Aggregates and events: `.cursor/skills/ddd-architecture/contexts.md`.

1. **IdentityAccess** — users, roles, session
2. **CRM** — B2B customers, contacts, countries in UAE/GCC/EU/CIS/Russia
3. **Commercial** — quotes and bookings: mode (air/road/trading), goods type, weekly vs monthly
4. **Freight** — shipments, cargo, tracking, FTL/LTL
5. **Warehouse** — locations, 3PL stock vs owned trading stock
6. **Trading** — SKUs (auto spare parts, perfumes, cosmetics, hygiene, cleaning supplies) and trading orders
7. **Finance** — invoices in AED, compensation claims
8. **Audit** — append-only log of domain events

Defer: public customer portal, sea as a first-class mode, fleet master, Arabic UI, multi-company tenancy.

## Language and copy

- UI default: English. Russian in the same release (`ru` already exists on the marketing site).
- Prepare layout for RTL. Do not ship Arabic strings until asked.
- Use company words: shipment, cargo, consignment, 3PL, FTL, LTL, air freight, road freight, trading, compensation, door-to-door, refrigerated.
- Never use “Talal Logistics”. That string is leftover marketing-site copy.
- Errors name the field and the fix. No error codes as the only message.

## Money, time, identifiers

- Currency: AED. Store as `decimal.Decimal`. Never IEEE float.
- Display amounts with a thin space thousands separator and 2 fraction digits unless the user asks otherwise.
- Store timestamps in UTC. Display `Asia/Dubai`. Booking hours on the site are Mo–Fr 08:30–17:30 Dubai time.
- Phone example from the site: `+971 58 304 2287`. Store E.164.
- Shipment numbers are opaque business ids, not database integers in the URL if a sequential id would leak volume.

## Data that must not leak across customers

Shipment, invoice, claim, quote, and stock-owner records are tenanted by customer (and by 3PL owner when goods are not ours). Every read/write path checks the caller can see that customer. Details in the cybersecurity skill.

## Status language (shipments)

Keep a small, visible set. Do not invent a 20-step customs engine on day one:

`draft → booked → in_transit → arrived → delivered → exception → claimed`

Refrigerated shipments must show a temperature note on the timeline when the user records one.

## Sources

Company pages listed in the root `README.md`. Do not treat third-party directories as stronger than the company’s own site.
