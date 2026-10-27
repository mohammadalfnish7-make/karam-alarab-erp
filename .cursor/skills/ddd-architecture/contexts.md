# Bounded contexts and aggregates

Build contexts in this order: IdentityAccess → CRM → Commercial → Freight → Warehouse → Trading → Finance. Audit listens from the first mutating context.

## IdentityAccess

- **User** (root): email, password hash, roles, active flag. MFA fields exist but unused.
- Invariants: cannot disable the last admin; password never on the entity as plain text.
- Events: `UserRegistered`, `UserDeactivated`.

## CRM

- **Customer** (root) + child **Contact**.
- Invariants: at least one contact before the customer can be quoted (enforce when Commercial asks, or require it on `Customer.activate()`).
- Holds country in UAE/GCC/EU/CIS/Russia as a value, not a free-form continent.
- Events: `CustomerRegistered`.
- Other contexts store `customerId` only.

## Commercial

- **Quote** (root): `customerId`, mode (`air` | `road` | `trading`), goods type, cadence (`weekly` | `monthly` | `once`), money estimate.
- Invariants: mode required; trading quotes need a goods type from the trading categories; cannot accept a cancelled quote.
- Events: `QuoteCreated`, `QuoteAccepted`, `QuoteCancelled`.
- Freight reacts to `QuoteAccepted` by creating a **draft** `Shipment` (new transaction).

## Freight

- **Shipment** (root) + child **TrackingEvent** (append-only).
- Value objects: `Cargo` (weight, CBM, temperature note), `TransportMode` (air, road FTL/LTL/box/flatbed/refrigerated).
- Holds `customerId`, optional `quoteId`.
- Status machine lives on the root (see backend reference). Illegal transition throws a domain error → HTTP 409.
- Events: `ShipmentBooked`, `ShipmentInTransit`, `ShipmentArrived`, `ShipmentDelivered`, `ShipmentMovedToException`.
- Refrigerated cargo: a tracking event may include `TemperatureNote`; the root does not skip status because temperature is missing — ops records it when they have it.

## Warehouse

- **Location** (root): warehouse/bin in Sharjah.
- **StockPosition** (root): `skuId?`, `customerId?` (3PL owner), `locationId`, on-hand qty.
- Invariants: on-hand never negative; owned trading stock and 3PL stock are different positions (different `customerId` / ownership).
- Events: `StockReceived`, `StockPicked`.
- Do not update stock inside the `Shipment` aggregate.

## Trading

- **Sku** (root): category in {auto spare parts, perfumes, cosmetics, hygiene, cleaning supplies}.
- **TradingOrder** (root): `customerId`, lines as children (`skuId`, qty, money).
- Events: `SkuDefined`, `TradingOrderConfirmed`.
- Warehouse listens to `TradingOrderConfirmed` to pick.

## Finance

- **Invoice** (root): `customerId`, optional `shipmentId` or `tradingOrderId`, lines, `Money` total, status `draft | posted`.
- **CompensationClaim** (root): `shipmentId`, `customerId`, `Money`, status.
- Invariants: cannot post an invoice twice; claim only from a shipment in `exception` (check via `shipmentId` + policy, not by loading Freight entities into this aggregate). Prefer reacting to `ShipmentMovedToException` to *open a draft claim*, then finance posts.
- Events: `InvoicePosted`, `ClaimOpened`, `ClaimSettled`.
- Dual control: posting is a command on the aggregate, not a PATCH of `status`.

## Audit

- Append-only **AuditEntry** from integration events. No business invariants besides immutability.

## Folder example (Freight)

```
backend/freight/src/            # later slice; mirror backend/core layout
  domain/
    shipment.py                 # aggregate root
    tracking_event.py
    cargo.py                    # value object
    transport_mode.py
    shipment_status.py
    events.py
    ports.py                    # ShipmentRepository protocol
  application/
    book_shipment.py
    move_shipment.py
    get_shipment.py
  database/
    models/
    repositories/
  api/
    shipment_router.py
    shipment_dto.py
```

`book-shipment.handler.ts` loads nothing from Finance. After save, it publishes `ShipmentBooked`.
