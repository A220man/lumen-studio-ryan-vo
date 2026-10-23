# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

vtable-resolver-core

## Roadmap

### skeleton — FastAPI + React + Vite skeleton

Status: done

Acceptance:
- GET /health responds
- Dev servers run locally
- Typed API client generated from routes

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `frontend/src/main.tsx`, `frontend/src/App.tsx`

Tests: `backend/tests/test_health.py`

### vtable-resolver-core — Indirect call resolver: resolve vtable[index] to function names

Status: done

Acceptance:
- Create a vtable definition with slot layout
- Resolve indirect calls in code snippet
- Export resolution results as JSON
- Resolve hexadecimal indices (0xN, 0XN) alongside decimal indices

Implementation: `backend/app/services/vtable_resolver.py`, `backend/app/api/resolver.py`, `frontend/src/pages/ResolverDashboard.tsx`, `frontend/src/components/VtableForm.tsx`, `frontend/src/components/ResolverPanel.tsx`, `frontend/src/components/ResultsList.tsx`, `frontend/src/api/client.ts`

Tests: `backend/tests/test_vtable_resolver.py`, `backend/tests/test_api.py`, `frontend/tests/resolver.test.tsx`

### auth-oidc — Keycloak OIDC authorization-code login with state+nonce+PKCE

Status: planned

Acceptance:
- OIDC login callback flow
- Issued token signature/issuer/audience validation
- viewer/analyst/admin RBAC on data endpoints

### llm-adapters — Multi-provider LLM adapter for opt-in advisory explanations

Status: planned

Acceptance:
- OpenAI-compatible
- Anthropic messages
- Gemini generateContent adapters with redacted errors

### dockerize — Dockerfiles, dockerignore, nonroot compose.yaml with Keycloak

Status: done

Acceptance:
- Backend Dockerfile builds
- Frontend Dockerfile builds
- compose.yaml starts app + Keycloak

Implementation: `backend/Dockerfile`, `backend/.dockerignore`, `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx.conf`, `compose.yaml`, `keycloak-realm.json`

### ci — CI workflow: backend tests, frontend build/test, Docker builds

Status: done

Acceptance:
- pytest passes
- vite build + vitest pass
- docker buildx builds both images

Implementation: `.github/workflows/ci.yml`

