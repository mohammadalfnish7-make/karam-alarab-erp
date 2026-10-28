# Karam Al Arab ERP — frontend

Vite + React + TypeScript SPA. Talks to FastAPI over REST with HttpOnly session cookies.

## Layout (clean / easy to refactor)

```
src/
  app/           # composition: providers, router, 401 bridge
  pages/         # route screens (thin)
  features/auth/ # session API, hooks, route/permission gates
  shared/
    api/         # http client + error envelope + DTOs
    i18n/        # en + ru
    ui/          # small primitives
    config/      # env
```

Dependency direction: `pages → features → shared`. `app` wires them. Do not import pages from features.

## Run

**Production-like (Docker)** — from repo root: `docker compose up --build` (see [`../docker/README.md`](../docker/README.md)).

**Dev**

```bash
# API first (from repo root)
cd backend/core && uv run uvicorn main:app --app-dir src --reload --port 8000

# Web
cd frontend
cp .env.example .env   # optional
npm install
npm run dev
```

Open [http://127.0.0.1:5173/en/login](http://127.0.0.1:5173/en/login). Russian: `/ru/login`.

Login uses `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` from the API `.env`.

## Docker image

```bash
docker build -t karam-web .
# Serves the SPA on :80 and expects an upstream hostname `api:8000` for /api (compose provides it).
```


## Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite on :5173 with `/api` → :8000 proxy |
| `npm run build` | Typecheck + production bundle |
| `npm run gen:api` | Regenerate OpenAPI types (API must be up) |

## Auth notes

- Cookie session (`karam_session`), never localStorage tokens
- `GET /users/me` restores session; anonymous → `null`
- UI permission gates are UX only; the API enforces access
