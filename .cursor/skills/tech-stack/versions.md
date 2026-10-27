# Latest stable snapshot

Checked **27 Oct 2026** from python.org, PyPI `latest`, npm `latest`, nodejs.org, postgresql.org. Re-check before scaffold or adding a dependency. Do not use RC, beta, alpha, `next`, or yanked releases.

## Runtimes

| Piece | Latest stable | Source | Notes |
| --- | --- | --- | --- |
| Python | **3.15.2** (repo runs **3.14.7**) | [python.org](https://www.python.org/downloads/release/python-3152/) | 3.16 is pre-release. uv has no 3.15.2 build yet (only `3.15.0rc1`). `apps/api` pins `>=3.14,<3.16` until 3.15 is on uv without RC. |
| Node.js | **24.22.1 LTS** (Krypton) | [nodejs.org](https://nodejs.org/en/blog/release/v24.22.1) | 26.12.1 is Current, not LTS. Use LTS for this ERP. React Router needs ≥22.22. |
| PostgreSQL | **18.6** | [postgresql.org](https://www.postgresql.org/docs/release/18.6/) | 19 is RC. Skip RC. |

## Python packages (PyPI latest, not yanked)

| Package | Version | Registry |
| --- | --- | --- |
| fastapi | 0.162.0 | [PyPI](https://pypi.org/project/fastapi/) |
| uvicorn | 0.54.0 | [PyPI](https://pypi.org/project/uvicorn/) |
| pydantic | 2.14.1 | [PyPI](https://pypi.org/project/pydantic/) |
| sqlalchemy | 2.1.6 | [PyPI](https://pypi.org/project/sqlalchemy/) |
| alembic | 1.20.1 | [PyPI](https://pypi.org/project/alembic/) |
| psycopg | 3.3.6 | [PyPI](https://pypi.org/project/psycopg/) |
| argon2-cffi | 25.1.0 | [PyPI](https://pypi.org/project/argon2-cffi/) |
| pytest | 9.1.1 | [PyPI](https://pypi.org/project/pytest/) |
| ruff | 0.17.3 | [PyPI](https://pypi.org/project/ruff/) |

Install extras: `uvicorn[standard]`, `psycopg[binary]`.

## JavaScript packages (npm `latest`)

| Package | Version | Registry |
| --- | --- | --- |
| react / react-dom | 19.3.1 | [npm](https://www.npmjs.com/package/react) |
| @types/react | 19.3.0 | [npm](https://www.npmjs.com/package/@types/react) |
| typescript | 7.0.2 | [npm](https://www.npmjs.com/package/typescript) | typescript-eslint 8.72.1 peer is `>=4.8.4 <6.1.0`. Web app keeps TS 7.0.2 and installs eslint with `legacy-peer-deps` until the plugin supports 7. |
| vite | 8.3.5 | [npm](https://www.npmjs.com/package/vite) |
| react-router | 8.5.0 | [npm](https://www.npmjs.com/package/react-router) |
| @tanstack/react-query | 5.105.0 | [npm](https://www.npmjs.com/package/@tanstack/react-query) |
| tailwindcss | 4.3.3 | [npm](https://www.npmjs.com/package/tailwindcss) |
| i18next | 26.5.11 | [npm](https://www.npmjs.com/package/i18next) |
| react-i18next | 17.1.9 | [npm](https://www.npmjs.com/package/react-i18next) |
| @playwright/test | 1.64.1 | [npm](https://www.npmjs.com/package/@playwright/test) |

## Re-check commands

```bash
# Python
python3 -c "import json,urllib.request as u; print(json.load(u.urlopen('https://pypi.org/pypi/fastapi/json'))['info']['version'])"

# npm
npm view react version
npm view vite version

# Runtimes
# https://www.python.org/downloads/
# https://nodejs.org/dist/index.json  (pick newest with lts != false)
# https://www.postgresql.org/support/versioning/
```

If a new `latest` is higher than this table and is not a pre-release, use the newer one and update this file.
