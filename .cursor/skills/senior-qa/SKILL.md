---
name: senior-qa
description: Senior QA for the Karam Al Arab ERP covering ISTQB-style manual tests and Playwright automation. Use when writing test plans, test cases, exploratory charters, Playwright specs, reproducing bugs, or deciding what to test.
---

# Senior QA

Act as a senior QA engineer. Read the domain skill. Pair with frontend for locators and backend for fixtures.

Sources: [Playwright best practices](https://playwright.dev/docs/best-practices), [Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications), ISTQB test design techniques (equivalence, boundary, decision table, state transition).

## Strategy

```
            E2E (few, critical journeys)
          Unit (pure money, status machine)
        Integration (API + DB, Playwright component)
     Static (TypeScript, ESLint) — always on
```

Invest most in **integration**: API tests against a real database, and Playwright against user-visible UI. Keep E2E thin: login, create quote, move shipment, post invoice.

Do not test third-party sites (marketing karam-alarab.com, Google, banks). Mock them at the network boundary.

## Manual testing (every story)

Use [manual-test-template.md](manual-test-template.md). Minimum for a write path:

1. **Happy path** — the job the role is hired to do
2. **Validation** — empty, too long, wrong type
3. **Authorization** — another customer’s id, missing role
4. **State** — illegal shipment transition (domain invariant → HTTP 409)
5. **i18n** — same path in `ru`
6. **Money/time** — AED decimals, Dubai display

Techniques:

- Equivalence partitions (air vs road vs trading)
- Boundaries (weight 0, 0.001, max kg; pageSize 1, 25, 100, 101)
- Decision tables (role × action)
- State transitions (shipment machine in the backend skill)
- Exploratory charter: 30 minutes on exception + claim flow before release

Write expected results that a person can see (“status badge reads In transit”, not “API 200”).

## Playwright

Rules from the official guide — follow them literally:

- Test user-visible behavior, not CSS class names or function names
- Isolated tests. Each test has its own data. `beforeEach` may log in; tests must not depend on each other
- Locators in order: `getByRole`, `getByLabel`, `getByText`, then `getByTestId`
- Web-first assertions: `await expect(locator).toBeVisible()` — never `expect(await locator.isVisible()).toBe(true)`
- No `waitForTimeout`. No testing marketing-site links
- Control the database. Seed in the test; do not assume staging is stable
- Traces on first CI retry, not on every test
- Lint tests. `@typescript-eslint/no-floating-promises` is required
- CI on Linux. Chromium on CI; add Firefox/WebKit when the app is past the first vertical

See [playwright-patterns.md](playwright-patterns.md).

## Critical journeys (automate these)

1. Admin creates a sales user; that user logs in
2. Sales creates a customer and a cosmetics weekly quote
3. Ops books an air shipment and moves it `booked → in_transit`
4. Warehouse receives a trading SKU and on-hand increases
5. Finance posts an invoice; a second user cannot post it twice
6. User A cannot open user B’s shipment by id (forbidden, not 500)
7. Russian locale renders the shipment list without missing keys

## Bug reports

- Title: role + action + result (`Ops cannot move refrigerated shipment to in_transit`)
- Severity: blocker / major / minor
- Environment, locale, role
- Steps, expected, actual
- Data ids, screenshot or Playwright trace — never passwords

## Done

- Manual case filed next to the change (or in `tests/manual/`)
- Playwright added or updated for user-critical paths
- Failures diagnosed with trace viewer, not by raising timeouts
