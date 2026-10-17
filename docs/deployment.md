# Deployment Guide

## Prerequisites

- Docker 24+
- Docker Compose v2+
- (Optional, for OIDC) Keycloak 26+

## Local development

```bash
# Terminal 1: backend
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev

# Terminal 3: (optional) keycloak for OIDC testing
docker compose --profile auth up keycloak
```

## Docker Compose

```bash
# Demo mode (backend + frontend only, no auth)
docker compose --profile app up --build

# Full stack with Keycloak OIDC
KEYCLOAK_ADMIN_PASSWORD=change-me \
docker compose --profile app --profile auth up --build
```

| Service | Port (localhost) | Profile |
|---|---|---|
| Frontend (nginx) | 5173 | app |
| Backend (FastAPI) | 8000 | app |
| Keycloak | 8080 | auth |

## Production checklist

1. **TLS**: Place behind a TLS-terminating reverse proxy (nginx, Caddy,
   or Cloudflare). The backend binds to `0.0.0.0` in Docker; restrict
   via firewall rules or a reverse proxy.
2. **Database**: Create a host volume or Named Volume for persistence.
   The compose file uses `backend-data:/app/data`.
3. **Demo mode**: Set `DEMO_MODE=false` and `APP_ENV=production` in the
   backend environment. The app refuses to start if both are set.
4. **OIDC**: Configure Keycloak with the realm import
   (`keycloak-realm.json`). Set `KEYCLOAK_CLIENT_SECRET` and
   `LUMEN_CLIENT_SECRET` as environment variables.
5. **Backups**: Periodically copy `lumen.db` from the volume.

## TLS reverse proxy example (Caddy)

```caddyfile
lumens.studio {
    reverse_proxy localhost:5173
    encode gzip
    header {
        Strict-Transport-Security max-age=31536000
        X-Content-Type-Options nosniff
    }
}
```

## Backup & restore

```bash
# Backup (container running)
docker cp lumen-studio-backend:/app/data/lumen.db ./backup-$(date +%F).db

# Restore (stop backend first)
docker cp ./backup-2025-01-01.db lumen-studio-backend:/app/data/lumen.db
docker compose restart backend
```