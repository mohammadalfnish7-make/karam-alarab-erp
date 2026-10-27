# Core API (IdentityAccess)

See **[INDEX.md](INDEX.md)** for the folder map.

```bash
cp .env.example .env
# Set SEED_ADMIN_PASSWORD (12+ chars)
uv sync
uv run uvicorn main:app --app-dir src --reload --port 8000
uv run pytest
```
