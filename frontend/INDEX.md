# Frontend index

Signed-in SPA for Karam Al Arab ERP. Clean layering so auth, screens, and API can be swapped without a rewrite.

## Layers

| Folder | Role | Replace when… |
| --- | --- | --- |
| `src/app/` | Composition root (providers, router, 401 bridge) | Boot / routing changes |
| `src/pages/` | Thin screens | New routes |
| `src/features/auth/` | Session API, hooks, gates | Auth UX or cookie contract changes |
| `src/shared/api/` | HTTP client + error envelope + DTOs | OpenAPI regen / transport |
| `src/shared/i18n/` | `en` + `ru` messages | Copy |
| `src/shared/ui/` | Small primitives | Design system / shadcn |

Rule: `pages → features → shared`. Never import a page from a feature.

## Auth contract (backend)

| Method | Path | UI use |
| --- | --- | --- |
| POST | `/sessions` | Login |
| DELETE | `/sessions/current` | Logout |
| GET | `/users/me` | Session restore |

Cookie: HttpOnly `karam_session`. Dev proxy: Vite `/api` → `:8000`.

## Run

See [`README.md`](README.md).
