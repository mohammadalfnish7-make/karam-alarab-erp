# Defensive review checklist

Copy this into the PR or chat. Mark each line `pass`, `n/a`, or `fail` with a one-line fix.

## Access

- [ ] Every handler that takes an id loads the row and checks the caller may access it
- [ ] Missing row and unauthorized row look the same to the client (404)
- [ ] Role cannot call another module’s write (warehouse cannot post invoices)
- [ ] Deny by default if the permission table is unavailable

## Authn / session

- [ ] Login rate-limited
- [ ] Session invalidated on password change
- [ ] Cookie flags (HttpOnly, Secure, SameSite) or equivalent token storage
- [ ] No user id or role accepted from a client header

## Input / output

- [ ] Transport DTO is not the domain model; map at the interface adapter
- [ ] DTO rejects unknown fields (mass assignment)
- [ ] Domain invariants run on the aggregate (status, money, stock), not only Pydantic validators
- [ ] SQLAlchemy parameterized; no string-built SQL; persist one aggregate per transaction
- [ ] Upload allowlist and size cap (or no uploads in this change)
- [ ] JSON error envelope has no stack trace

## Money and cargo

- [ ] Invoice/claim post is a single transaction with an audit row
- [ ] Status changes go through the state machine
- [ ] Tracking notes are stored as text, rendered encoded

## Config / supply chain

- [ ] New secrets are env vars only
- [ ] New dependency is pinned and justified
- [ ] CORS allowlist, not `*`
- [ ] Authenticated responses `Cache-Control: no-store`

## Logging

- [ ] Authn/authz failures logged with request id and actor
- [ ] No password, token, or full card/passport in logs

## Tests

- [ ] Automated test for the forbidden object id
- [ ] Automated test for validation failure

Do not attach exploit steps or payloads to this checklist.
