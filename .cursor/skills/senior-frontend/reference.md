# Frontend reference

## App layout

```
apps/web/app/[locale]/(app)/
  layout.tsx          # shell: nav, user, locale
  page.tsx            # dashboard
  customers/
  quotes/
  shipments/
  warehouse/
  trading/
  invoices/
apps/web/components/  # ui primitives and domain widgets
apps/web/messages/en.json
apps/web/messages/ru.json
```

Route groups stay behind auth. Locale is in the path (`/en/shipments`, `/ru/shipments`).

## Component rules

- One component, one job. A shipment table does not fetch invoices.
- Colocate the loader, error boundary, and empty state with the page.
- Prefer composition over boolean prop forests (`<Button variant="primary">`, not `isPrimary isLarge isWarning`).
- Accessible names on icon-only buttons (`aria-label="Filter shipments"`).

## Fetching

```ts
// Good: server component loads the first page
const shipments = await api.shipments.list({ status, page });

// Good: client mutations via query client
await queryClient.invalidateQueries({ queryKey: ['shipments'] });

// Bad
const [shipments, setShipments] = useState([]);
useEffect(() => { fetch('/api/shipments').then(...) }, []);
```

## Forms

- Label every control. Errors on the field, not only a toast.
- Confirm before canceling a dirty money form.
- Disabled submit while in-flight; keep the typed values.

## What not to copy from karam-alarab.com

The public site is Bootstrap + sparse hero sections. The ERP is a signed-in tool. Reuse color, type, and logo mark only.
