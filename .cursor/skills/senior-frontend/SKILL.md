---
name: senior-frontend
description: Senior frontend engineering for the Karam Al Arab ERP. Use when building or reviewing React, Vite, TypeScript, client state, forms, tables, i18n, or any apps/web UI.
---

# Senior frontend

Act as a senior frontend engineer on a dense B2B ERP. Read the domain skill and `.cursor/skills/tech-stack/SKILL.md` first. Pair with the UI/UX skill for layout and brand. The API is FastAPI + DDD: consume OpenAPI DTOs over REST. Do not import `apps/api` Python into the web app.

Sources: [Thinking in React](https://react.dev/learn/thinking-in-react), [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html), [Google engineering practices](https://google.github.io/eng-practices/), [Vite](https://vite.dev/guide/).

## Stack

- React + TypeScript `strict` + Vite
- React Router with locale prefix (`/en/...`, `/ru/...`)
- Tailwind + shadcn/ui
- TanStack Query for server data. Do not mirror that data in `useState`
- react-i18next for `en` and `ru`
- Types generated from FastAPI OpenAPI

## Thinking in React (required)

1. Draw the UI as a component tree (page → filter bar → table → row → status).
2. List the data each component needs.
3. Identify the minimal state. If it can be computed, compute it.
4. Place state in the nearest common owner. Lift it; do not duplicate it.
5. One-way data flow: down as props, up as callbacks or mutations.

## TypeScript

- UTF-8. No `any`. Prefer `unknown` + narrowing.
- `interface` for object shapes. `type` for unions, tuples, mapped types.
- Do not disable `react-hooks/exhaustive-deps`. Fix the dependencies.
- Do not store derived values in state (filtered rows, totals, selected count).
- Do not hand-copy shipment DTO fields. Regenerate from OpenAPI when the API changes.

## State and data

- URL holds shareable filter/search/page state (`?status=in_transit&q=`).
- Forms validate on the client for UX; the FastAPI DTO is authoritative.
- Mutations: optimistic only when rollback is defined. Otherwise wait for the server and show pending.
- Never `console.log` in committed UI. Never leave `useEffect` that only syncs two states.

## ERP UI patterns

- Lists are tables with column headers, sort, filter, empty state, and row actions. Not marketing cards.
- Status is a colored badge plus text, never color alone.
- Money and dates go through shared formatters (`formatAed`, `formatDubaiDateTime`).
- Every screen: loading, empty, forbidden, and error. Forbidden is not a blank table.
- Keyboard: table row focus, Enter opens, Esc closes dialogs.

## i18n

- No user-visible English hardcoded in components. Strings in message files.
- Names, Sharjah addresses, and cargo descriptions can be mixed-script. `lang` on the document; `lang` on Russian passages when embedded.
- Do not concatenate translated sentences. Use ICU placeholders.

## Performance

- Paginate on the server. Do not download “all shipments” to the browser.
- Dynamic-import heavy widgets (maps, PDF).
- Images: size and alt. Logo is SVG/text, not a screenshot.

## Done

- Types pass. Lint passes.
- Changed flow verified in the browser (click, type, submit), not only a screenshot.
- Matches UI/UX brand tokens.
- New user-critical path has a Playwright spec (QA skill).

See [reference.md](reference.md) for file layout and component rules.
