# Docker deploy

One compose stack: **Postgres + FastAPI + nginx SPA**. The browser talks only to nginx; `/api` is proxied to the API so the session cookie stays first-party.

```
browser → web(:8080) ─┬─ /        → static React
                      └─ /api/*   → api:8000/*
api → db:5432
```

## First run (this machine or a VPS)

```bash
cp .env.example .env
# Set SEED_ADMIN_PASSWORD (12+ chars). Adjust WEB_ORIGIN if the host/port differs.

docker compose up --build -d
```

Open http://127.0.0.1:8080/en/login (or your server IP / domain with the same port).

```bash
docker compose ps
docker compose logs -f api
curl -s http://127.0.0.1:8080/health
```

Stop: `docker compose down` (add `-v` only if you intend to wipe the database volume).

## Move to a server

1. Clone the repo (or `git pull`) on the server.
2. Copy `.env` (or create from `.env.example`). Set:
   - `WEB_ORIGIN` to the public URL staff will use (e.g. `http://203.0.113.10:8080` or `https://erp.example.com`)
   - `SEED_ADMIN_PASSWORD` / `POSTGRES_PASSWORD` to strong values
3. `docker compose up --build -d`
4. Open the firewall for `WEB_PORT` (default 8080), or put Caddy/Traefik in front on 443 and set `ENVIRONMENT=production` + `WEB_ORIGIN=https://…`.

Images are self-contained; you only need Docker Engine + Compose on the host.

## Build images alone

```bash
docker compose build
# or
docker build -t karam-api ./backend
docker build -t karam-web ./frontend
```

## Notes

- SPA build bakes `VITE_API_BASE_URL=/api`. Do not point the browser at `:8000` in this layout.
- `ENVIRONMENT=production` turns on Secure cookies — login over plain HTTP will fail. Use TLS first.
- Uploads live in the `karam_uploads` volume; Postgres data in `karam_pg` (mounted at `/var/lib/postgresql` for Postgres 18+).
- API image runs `uvicorn main:build_app --factory` (not `main:app` — that attribute is lazy/`None` at import).
