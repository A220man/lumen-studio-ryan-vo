# Architecture

## Overview

Lumen Studio is an AI/ML reverse-engineering assistant that resolves
indirect function calls in decompiled C/C++ code. The application follows
a backend-driven API pattern with a React single-page application front
end.

```
Browser ──HTTP──► React SPA ──HTTP/JSON──► FastAPI ──SQLite──► lumen.db
                                        ▲
                                        │
                                   (OIDC R2)
                                        │
                                        ▼
                                    Keycloak
```

## Backend

### Entry point

`backend/app/main.py` exports `create_app()` and a module-level `app`
instance. Both Docker (`CMD uvicorn app.main:app`) and local development
(`PYTHONPATH=backend uvicorn app.main:app`) use the same entry point.

### Modules

| Module | Responsibility |
|---|---|
| `app/core/config.py` | Env-driven `Settings` (demo mode, DB URL, OIDC, LLM) |
| `app/core/database.py` | Thread-safe SQLite wrapper with schema init |
| `app/models/schemas.py` | Pydantic request/response models |
| `app/services/vtable_resolver.py` | Deterministic pattern engine |
| `app/api/health.py` | `/health` and `/version` endpoints |
| `app/api/resolver.py` | Vtable CRUD + resolution workflow endpoints |
| `app/api/dependencies.py` | `get_current_user` (demo mode or 401) |

### Persistence

SQLite is used with parameterized queries. The schema has two tables:

- **vtables**: `id`, `name`, `field_name`, `base_address`, `slots` (JSON),
  `created_at`, `updated_at`.
- **resolutions**: `id`, `vtable_id` (FK, cascade), `code`, `matches`
  (JSON), `created_at`.

### Domain engine

`VtableResolver` matches `FIELD[INTEGER]` patterns using a compiled regex:

```
\b{field_name}\s*\[\s*(\d+)\s*\]
```

For each match, the engine:
1. Extracts the integer index.
2. Looks up the corresponding slot in the user-defined slot list.
3. Returns a `ResolutionMatch` with line/column, expression, index,
   resolved function (or `null` with an advisory note).

`MultiVtableResolver` extends this to handle code referencing multiple
vtables with different field names, de-duplicating matches by position.

### Demo mode

When `DEMO_MODE=true` (default in development), the API requires no
authentication and binds to `127.0.0.1`. Startup refuses if
`APP_ENV=production` and `DEMO_MODE=true`.

## Frontend

### Stack

- React 18 + TypeScript + Vite
- No CSS framework — hand-written, responsive styles
- Vitest + React Testing Library for tests
- Typed API client (`src/api/client.ts`) mirrors backend schemas

### State flow

`ResolverDashboard` holds all state (vtables, selected vtable, code,
resolution result). Child components are presentational:

- `VtableForm`: create a vtable definition (name, field, slots).
- `ResolverPanel`: select a vtable, paste code, trigger resolution.
- `ResultsList`: display matched calls in a table, export as JSON.

### API client

The `api` object in `src/api/client.ts` provides typed methods matching
the backend routes. All methods use `fetch` with proper error handling.
The base URL defaults to `/api/v1` for Vite proxy support.

## Deployment

### Local (Docker Compose)

```bash
docker compose --profile app up --build
```

### CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on `ubuntu-latest`:
1. Backend: `pytest`
2. Frontend: `tsc`, `vitest run`, `vite build`
3. Docker: build both images (no push)

### Production

A TLS reverse proxy (nginx, Caddy, or Cloudflare) should terminate TLS
and proxy to the backend. See [deployment.md](./deployment.md).