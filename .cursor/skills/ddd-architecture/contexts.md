# Bounded contexts and aggregates

Build contexts in this order: IdentityAccess → WorkManagement → Freight → Warehouse. Audit listens from the first mutating context.

Removed from this product cut: CRM, Commercial, Trading, Finance.

## IdentityAccess

- **User** (root): email, password hash, roles, active flag. MFA fields exist but unused.
- Invariants: cannot disable the last admin; password never on the entity as plain text.
- Events: `UserRegistered`, `UserDeactivated`, `UserRolesChanged`, `UserPasswordChanged`, `LoginFailed`.

## WorkManagement

- **TaskType** / **Workflow** (admin config): no hardcoded business catalog; clients fetch types.
- **Task** (root): type, status (workflow graph), title, assignee, steps, comments, attachments, entity links, peer links.
- **NotificationChannel** (admin config): editable name + webhook URL + secret; fan-out on assign.
- **Notification** (inbox): per-recipient in-app row for employee UI later.
- **WebhookDelivery**: durable per-channel outbox row; worker signs and POSTs with retries.
- Events: `TaskCreated`, `TaskAssigned`.
- Permissions: `work:read|create|update|transition|attach|admin`.
- Lives in `backend/core` for now (same process as IdentityAccess).

## Freight

- **Shipment** (root) + child **TrackingEvent** (append-only).
- Value objects: `Cargo`, `TransportMode`.
- Status machine on the root. Illegal transition → HTTP 409.
- Events: `ShipmentBooked`, `ShipmentInTransit`, `ShipmentArrived`, `ShipmentDelivered`, `ShipmentMovedToException`.
- Not built yet.

## Warehouse

- **Location** (root), **StockPosition** (root).
- Events: `StockReceived`, `StockPicked`.
- Not built yet.

## Audit

- Append-only **AuditEntry** from integration events. No business invariants besides immutability.
