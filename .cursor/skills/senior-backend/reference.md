# Backend reference

## Pagination envelope

```json
{
  "data": [],
  "page": 1,
  "pageSize": 25,
  "total": 0
}
```

Cap `pageSize` at 100. Default 25.

## Error envelope

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Weight must be greater than 0.",
    "fields": { "weightKg": "Weight must be greater than 0." }
  }
}
```

`message` is safe to show. `code` is stable for the client.

## Shipment status machine

`draft → booked → in_transit → arrived → delivered`

`booked|in_transit|arrived → exception`

`exception → claimed` (finance) or back to `in_transit` (ops)

Reject any other transition with `409`.

## Context template

```
freight/
  freight.module.ts              # Nest composition root only
  domain/shipment.ts             # aggregate root
  domain/ports.ts
  application/book-shipment.handler.ts
  infrastructure/prisma-shipment.repository.ts
  interface/shipment.controller.ts
  interface/shipment.dto.ts
```

Controller does not inject the repository. Handler does not import Prisma.

## Headers

- `Content-Type: application/json; charset=utf-8` on JSON bodies
- `Cache-Control: no-store` on authenticated responses
- CORS allowlist of the web origin only
- Rate limit login and quote creation
