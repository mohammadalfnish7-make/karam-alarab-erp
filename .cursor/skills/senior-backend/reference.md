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
  router.py                              # FastAPI APIRouter, composition only
  domain/shipment.py                     # aggregate root
  domain/ports.py
  application/book_shipment.py
  infrastructure/sqlalchemy_shipment_repository.py
  interface/shipment_router.py
  interface/shipment_dto.py              # Pydantic, extra="forbid"
```

Router does not use the SQLAlchemy session for business rules. Handler does not import FastAPI.

## Headers

- `Content-Type: application/json; charset=utf-8` on JSON bodies
- `Cache-Control: no-store` on authenticated responses
- CORS allowlist of the web origin only
- Rate limit login and quote creation
