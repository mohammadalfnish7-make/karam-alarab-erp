---
name: senior-ui-ux
description: Senior UI/UX for the Karam Al Arab ERP. Use when designing screens, flows, navigation, empty states, visual hierarchy, accessibility, brand tokens, or reviewing whether an interface is usable for warehouse, freight, trading, and finance staff.
---

# Senior UI / UX

Act as a senior product designer for a complex enterprise app. Read the domain skill. Pair with frontend for implementation.

Sources: [Nielsen 10 heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) (reviewed 2024), [heuristics for complex applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/) AA.

## Product stance

This is a **daily ops tool**, not a brochure. The marketing site is sparse and hero-driven. The ERP is dense, keyboard-friendly, and status-first. Reuse brand tokens from [brand.md](brand.md) only.

Primary jobs: find a shipment, update its status, quote a booking, move stock, issue an invoice, answer “where is the cargo?”.

## Heuristics (apply every screen)

1. **Visibility of system status** — shipment status, stock on-hand, save state, and who last updated. Waits over ~10s need progress with steps, not a spinner-only “Please wait”.
2. **Real world** — FTL, LTL, air, road, 3PL, compensation. No invented SAP codes.
3. **User control** — Cancel, close, and undo for reversible edits. Draft quotes must be discardable. Money posts need a confirm step, not undo after the fact.
4. **Consistency** — same primary action top-right of a page. Plus means add, never expand. Same words for the same thing.
5. **Error prevention** — disable illegal status transitions; preview invoice totals before post; confirm delete of a customer with open shipments.
6. **Recognition over recall** — visible filters, saved views, customer typeahead with recent accounts. Do not require memorizing ids.
7. **Flexibility** — keyboard shortcuts for power users; labeled buttons for new staff. Tables support column density.
8. **Minimalism** — no decorative icons on a list of one item type. Stage advanced customs fields behind a disclosure.
9. **Error recovery** — “Could not display data. Contact admin” is a fail. Name the cause and the next action.
10. **Help in context** — short field hints (CBM, temperature band). No forced tour.

## Information architecture

Signed-in shell:

Dashboard · Customers · Quotes · Shipments · Warehouse · Trading · Invoices · Admin

Dashboard answers: shipments in exception, quotes awaiting reply, stock below a simple threshold, claims open. Not marketing KPIs.

## Accessibility (WCAG 2.2 AA)

- Contrast: text ≥ 4.5:1, UI chrome ≥ 3:1. Primary `#1769FF` on white is for large/semibold headings and buttons with white label, not small body text.
- Focus visible and not covered by a sticky header.
- Target size ≥ 24×24 px.
- Keyboard: all actions. Drag-and-drop warehouse boards need a non-drag alternative.
- Labels and headings describe purpose. Status messages (`role="status"`) for saves and errors without stealing focus unless blocking.
- Text resize 200% and reflow without horizontal scroll of the whole app (tables may scroll internally).
- Do not convey status by color alone.

## Interaction patterns

| Pattern | Use |
| --- | --- |
| Table + filters | Default for customers, shipments, invoices |
| Record header + tabs | Shipment detail: overview, timeline, documents, claims |
| Dialog | Short confirms, not whole record edits |
| Slide-over | Create quote / add SKU without leaving the list |
| Wizard | First-time booking only; experts get a single dense form |

## Copy

- Sentence case. Imperative buttons: “Create shipment”, “Post invoice”.
- English and Russian ship together. If a string is missing in `ru`, that is a bug, not a fallback forever.
- Phone and address examples match Sharjah / +971.

## Done

- Heuristic pass on the new flow (status visible, cancel exists, errors recoverable).
- AA contrast and keyboard path checked.
- Empty and forbidden states exist.
- Browser-verified at desktop (1280+) and a narrow ops laptop (1024). Warehouse floor may use a tablet: check 768 if the screen is warehouse-facing.

See [brand.md](brand.md) for tokens taken from the live site.
