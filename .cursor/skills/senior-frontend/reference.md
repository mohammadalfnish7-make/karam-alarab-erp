# Frontend reference

## App layout

```
apps/web/src/
  main.tsx
  routes/
    en/
    ru/                 # same screens, locale from path
  pages/
    dashboard.tsx
    customers/
    quotes/
    shipments/
    warehouse/
    trading/
    invoices/
  components/
  locales/en.json
  locales/ru.json
  api/                  # generated OpenAPI client
```

Authenticated layout wraps ops routes. Locale is in the path (`/en/shipments`, `/ru/shipments`).

## Component rules

- One component, one job. A shipment table does not fetch invoices.
- Colocate the loader, error boundary, and empty state with the page.
- Prefer composition over boolean prop forests (`<Button variant="primary">`, not `isPrimary isLarge isWarning`).
- Accessible names on icon-only buttons (`aria-label="Filter shipments"`).

## Fetching

```ts
// Good: query key + generated client
const { data } = useQuery({
  queryKey: ['shipments', { status, page }],
  queryFn: () => api.listShipments({ status, page }),
});

await queryClient.invalidateQueries({ queryKey: ['shipments'] });

// Bad
const [shipments, setShipments] = useState([]);
useEffect(() => { fetch('/shipments').then(...) }, []);
```

## Forms

- Label every control. Errors on the field, not only a toast.
- Confirm before canceling a dirty money form.
- Disabled submit while in-flight; keep the typed values.

## What not to copy from karam-alarab.com

The public site is Bootstrap + sparse hero sections. The ERP is a signed-in tool. Reuse color, type, and logo mark only.
