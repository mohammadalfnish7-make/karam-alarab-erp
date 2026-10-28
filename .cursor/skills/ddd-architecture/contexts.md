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
- Events: `TaskCreated`, `TaskAssigned`.
- Permissions: `work:read|create|update|transition|attach|admin`.
- Package: `backend/work` (imports platform `backend/core` only). Assign notify is handled by **Notifications**.

## Notifications

- **NotificationChannel** (admin config): name + webhook URL + secret.
- **Notification** (inbox): per-recipient in-app row.
- **WebhookDelivery**: durable outbox; worker signs and POSTs with retries.
- Input: `AssignNotifyCommand` (adapted from `TaskAssigned` in composition root — notify does not import work).
- Package: `backend/notify` (imports `core` only).

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

## Core ProcessTrace (cross-cutting)

- Shared `TraceRecorder` + `core_process_traces` / `core_process_trace_steps` in `backend/core`.
- After-commit fan-out and event handlers should `start` / `step` / `succeed|fail|partial` with a stable `correlation_id` (usually domain `event_id`) and `request_id`.
- Query via `GET /process-traces` (`process:read`). Do not invent per-context trace tables for Freight/Warehouse.
