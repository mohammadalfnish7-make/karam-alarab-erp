# Agent instructions — Karam Al Arab ERP

You are building the internal ERP for Karam Al Arab (karam-alarab.com). Read the matching skill before writing code, tests, UI, or a security opinion. The skills are the senior bar for this repo.

## Always

1. Read `.cursor/skills/karam-alarab-domain/SKILL.md`, `.cursor/skills/ddd-architecture/SKILL.md`, and `.cursor/skills/tech-stack/SKILL.md`.
2. Architecture is DDD: one bounded context, one aggregate per write, other contexts by id and events.
3. Stack is FastAPI (Python) + React (Vite/TypeScript). Always the latest stable from PyPI/npm (not RC). No NestJS, Next.js, or Prisma. See `.cursor/skills/tech-stack/versions.md`.
4. Use company words: shipment, cargo, 3PL, FTL, LTL, trading, compensation. English UI default; Russian must not lag.
5. Money is decimal in AED. Timestamps store UTC and display `Asia/Dubai`.
6. Do not implement exploits, attack payloads, or unauthorized access procedures. Security work is defensive: review, harden, test secure behavior.
7. Do not start a new module until the previous sequence step in `README.md` can be demoed.

## Load by task

| If you are… | Read |
| --- | --- |
| Adding a module, table, aggregate, or event | `.cursor/skills/ddd-architecture/SKILL.md` |
| Choosing a library or folder layout | `.cursor/skills/tech-stack/SKILL.md` |
| Changing UI, React, Vite, CSS, client state | `.cursor/skills/senior-frontend/SKILL.md` and `.cursor/skills/senior-ui-ux/SKILL.md` |
| Changing FastAPI routers, SQLAlchemy, jobs | `.cursor/skills/senior-backend/SKILL.md` |
| Designing a screen, flow, or component | `.cursor/skills/senior-ui-ux/SKILL.md` |
| Writing or running tests | `.cursor/skills/senior-qa/SKILL.md` |
| Reviewing risk, authz, secrets, headers | `.cursor/skills/senior-cybersecurity/SKILL.md` |
| Planning scope | Use the CTO plan template; keep README sequence |

## Definition of done

- Python types and TypeScript compile. No `any`.
- Authorization is checked on the server for every object id.
- UI has empty, loading, and error states, and a visible status.
- New write paths have a manual test case and a Playwright path if they are user-critical.
- Browser verification for any user-visible change.

Public site copy that still says “Talal Logistics” is a marketing-site bug. Never copy it into this product.
