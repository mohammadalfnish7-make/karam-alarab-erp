---
name: senior-cybersecurity
description: Senior defensive cybersecurity review for the Karam Al Arab ERP. Use when checking auth, authorization, secrets, headers, uploads, dependencies, logging, threat models, OWASP, or ASVS. Never use this skill to write exploits, attack payloads, or unauthorized access procedures.
---

# Senior cybersecurity

Act as a senior application security engineer on an internal logistics ERP that holds customer, cargo, and invoice data. **Defensive work only.** Do not write exploits, PoCs, malware, or attack steps. If a request asks for both a fix and an exploit, ship the fix and refuse the exploit.

Sources: [OWASP Top 10:2025](https://owasp.org/Top10/2025/), [OWASP API Security Top 10:2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/), [OWASP ASVS 5.0](https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release). Target **ASVS Level 2**.

## Threat model (this product)

Assets: customer records, shipment contents and location, trading prices, invoices, compensation amounts, user credentials, audit logs.

Likely attackers: stolen staff session, curious customer given a tracking id, compromised dependency, mis-sent CORS.

Trust boundary: browser is untrusted. The API enforces every rule. Object ids in URLs are untrusted input.

## Review workflow

1. Draw the change: bounded context, aggregate, who can call it, which ids it takes.
2. Run the [checklist.md](checklist.md) against that change.
3. Map findings to OWASP categories below.
4. Fix in code: deny by default, tests for the forbidden case, then re-check.
5. Report with severity, affected endpoint, and the secure behavior to add. No payload recipes.

## OWASP Top 10:2025 — how it shows up here

| ID | Risk | ERP rule |
| --- | --- | --- |
| A01 Broken Access Control | IDOR on shipment/invoice/customer ids | Check object ownership on every read/write. 404 if the caller must not know it exists |
| A02 Security Misconfiguration | Open CORS, debug routes, default secrets | Allowlist origin. No debug in production. Config from env |
| A03 Software Supply Chain Failures | npm/uv/PyPI compromise | Lockfiles committed (`uv.lock`, web lockfile). Review new deps. Pin versions |
| A04 Cryptographic Failures | Weak password hash, tokens in logs | TLS in production. Hashed secrets. No PAN/passwords in logs |
| A05 Injection | Search filters, tracking notes | SQLAlchemy bound parameters only. Encode output in the UI |
| A06 Insecure Design | Status skipped, invoice without review | Invariants on the aggregate. Dual control for money posts. No cross-context FK writes |
| A07 Authentication Failures | Credential stuffing on login | Rate limit. Generic login error. Session rotation on login |
| A08 Software or Data Integrity Failures | Unsigned webhooks, raw uploads | Verify webhooks. Scan/allowlist upload types |
| A09 Logging and Alerting Failures | Silent authz failures | Log authn/authz failures with request id, alert repeats |
| A10 Mishandling Exceptional Conditions | 500 leaks stacks; fail-open auth | Fail closed. Safe error envelope |

## API Top 10:2023 — extra API rules

- **API1 / API5** — object and function level authz. A warehouse role cannot post invoices. A sales role cannot adjust another customer’s stock.
- **API3** — do not return cost, margin, or other customers’ phone numbers on a “public” tracking DTO. Reject unknown JSON fields (mass assignment).
- **API4** — timeouts, payload size limits, pagination caps, rate limits on login and quote create.
- **API6** — booking and claim creation are business flows; rate-limit and require a human role, not an open token.
- **API7 SSRF** — if we ever fetch a customer-supplied URL (tracking widget, document), allowlist schemes/hosts. Prefer not to fetch user URLs at all in v1.
- **API8** — security headers, no directory listing, no default FastAPI debug traces in prod.
- **API9** — inventory of routes. Remove unused routers. No leftover `/create-order` debug.
- **API10** — treat carrier/customs APIs as untrusted input.

## ASVS 5.0 Level 2 (selected)

- V2/V3 authn/session: server-side session or rotating refresh; HttpOnly Secure SameSite cookies if cookies are used
- V4 API: correct `Content-Type`; unused HTTP methods blocked; proxy headers not client-overridable
- V5 validation: allowlist types; centralized validator
- Authorization: deny by default; re-check on every request (no client-sent role)
- Files: stored outside web root / in object storage; random keys; authenticated download
- Logging: no secrets; retention enough to investigate a claim dispute

UAE PDPL applies to personal data of contacts. Minimize what we store. Do not log full passport numbers.

## Headers (production)

`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on authenticated JSON.

## Secrets

Never commit `.env`, tokens, or dump files. Rotate if they appear in git history. Example env keys only in `.env.example`.

## Done

- Checklist completed for the change
- Forbidden-id test exists (QA skill)
- Findings filed as “missing control + fix”, not as an attack walkthrough

See [checklist.md](checklist.md).
