# Lumen Studio — Ryan Vo | AI & Machine Learning

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


## Problem and approach

When reverse engineering C++ binaries in Ghidra, the decompiler often
leaves indirect function calls unresolved as opaque expressions like
`(*this->vtable[6])(local_20)`. The analyst must manually cross-reference
the listing view to discover that slot 6 maps to — say —
`MyClass::doAction`. **Lumen Studio** addresses this by resolving
`vtable[INDEX]` indirection patterns against user-defined vtable layouts,
mapping each integer slot index to its concrete function name.

The **AI/ML purpose** is twofold:

1. **Deterministic pattern engine** (offline, no LLM key required): a
   regex-based parser identifies `FIELD[INTEGER]` indirections in decompiled
   C snippets and matches them against ordered slot lists. This provides a
   reproducible baseline with 100 % precision on integer-indexed calls.
2. **Opt-in LLM advisory layer** (planned for R2): an OpenAI-compatible /
   Anthropic / Gemini / Ollama adapter that summarizes resolved calls and
   explains slot assignments in natural language, grounded in the actual
   resolution records.

**Intended user**: reverse engineers and vulnerability researchers who work
with C++ binaries in Ghidra and need to resolve indirect calls quickly.

## Quick start (demo mode)

```bash
# Backend (Python 3.12)
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
# Frontend (Node 24)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The API is reachable at `http://127.0.0.1:8000/api/v1/`.

## Install & run with Docker

```bash
docker compose --profile app up --build
# Backend:   http://127.0.0.1:8000
# Frontend:  http://127.0.0.1:5173
```

## Tests

```bash
# Backend
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v

# Frontend
cd frontend && npm test
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  Browser             React + Vite SPA       │
│  (localhost:5173)      typed API client       │
└────────────┬───────────────────────────────┘
             │  HTTP/JSON
┌────────────┴───────────────────────────────┐
│  FastAPI backend    uvicorn                 │
│  /api/v1/health    /api/v1/vtables           │
│  /api/v1/resolutions                        │
│  services/vtable_resolver.py (domain engine)│
│  core/ SQLite persistence                   │
└────────────┬───────────────────────────────┘
             │  SQLite
┌────────────┴───────────────────────────────┐
│  lumen.db  (vtable definitions,            │
│            resolution records)              │
└───────────────────────────────────────────┘
```

```mermaid
graph TL
    B[Browser\nlocalhost:5173]
    SPA[React + Vite\nTyped API client]
    API[FastAPI\nuvicorn on :8000]
    DB[(SQLite\nlumen.db)]
    FE[Frontend\nnginx:80]
    BE[Backend\nnonroot:8000]

    B --> SPA
    subgraph Container
        FE -->|proxy /api/v1| BE
        BE --> DB
    end
    SPA -->|HTTP/JSON| BE
```

## Features

| Feature | Status |
|---|---|
| Vtable definition (name, field, slots) | ✅ R1 |
| Indirect call resolution (`vtable[N]` → function name) | ✅ R1 |
| Hex index support (`vtable[0x6]`, `vtable[0X10]`) | ✅ R1.1 |
| Resolution persistence & retrieval | ✅ R1 |
| JSON export of resolution results | ✅ R1 |
| Health & version endpoints | ✅ R1 |
| Keycloak OIDC PKCE login | 🚧 R2 |
| LLM advisory explanations (OpenAI/Anthropic/Gemini/Ollama) | 🚧 R2 |
| Switch / jump-table pattern recognition | 🚧 R2 |
| Multi-vtable batch resolution | 🚧 R2 |

## API reference

All routes under `/api/v1/`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/version` | Version & config summary |
| `POST` | `/vtables` | Create a vtable definition |
| `GET` | `/vtables` | List vtables (paginated) |
| `GET` | `/vtables/{id}` | Get a vtable |
| `DELETE` | `/vtables/{id}` | Delete a vtable (cascades) |
| `POST` | `/resolutions` | Resolve indirect calls in code |
| `GET` | `/resolutions` | List past resolutions |
| `GET` | `/resolutions/{id}` | Get a resolution with matches |

### Vtable definition

```jsonc
POST /api/v1/vtables
{
  "name": "MyClass::vtable",
  "field_name": "vtable",          // as it appears in the decompiler
  "base_address": "0x401000",      // optional
  "slots": ["fn_getType", "fn_addRef", null, "fn_method3"]
  // null = empty/unknown slot
}
```

### Resolution request

```jsonc
POST /api/v1/resolutions
{
  "vtable_id": 1,
  "code": "(*this->vtable[0])(arg1);"
}
```

### Resolution response

```jsonc
{
  "id": 1,
  "vtable_id": 1,
  "vtable_name": "MyClass::vtable",
  "code": "(*this->vtable[0])(arg1);",
  "matches": [
    {
      "line": 1,
      "column": 9,
      "expression": "vtable[0]",
      "field_name": "vtable",
      "slot_index": 0,
      "resolved_function": "fn_getType",
      "note": "resolved to fn_getType"
    }
  ],
  "created_at": "2025-01-01T12:00:00+00:00"
}
```

## AI/ML evaluation

### Reproducible baseline

```bash
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -v
```

### Data provenance

The test corpus is derived from Ghidra issue #516: the canonical example
`(*this->vtable[6])(local_20)` where the analyst needs to know which
function occupies slot 6. Additional test cases cover boundary indices
(0, last, out-of-range), empty slots (`null`), multiline snippets,
hexadecimal indices (`0xN`, `0XN`), and unknown field names.

### Measured results

| Metric | Value |
|---|---|
| Backend tests | 41 passed |
| Frontend tests | 5 passed |
| Pattern precision (integer + hex indices) | 100 % (41 engine-level assertions) |
| Pattern coverage | literal decimal & hex integer indices |

No ML model is trained or invoked in R1. The deterministic resolver is the
baseline. All measurements are from the test suite above.

### Failure cases

- **Variable indices** (`vtable[i]`): not matched (non-literal).
- **Multiple vtables with the same field name**: the resolver matches by
  `field_name`; overlapping definitions should use distinct field names.
- **LLM explanations**: not yet available (R2).

## Provider configuration

The LLM adapter is **opt-in**. Set `LLM_API_KEY` to enable advisory
summaries (planned R2). Providers are interchangeable via environment
variables:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | *blank* | Bearer token for the LLM provider |
| `LLM_PROVIDER` | `openai-compatible` | `openai-compatible`, `anthropic`, `gemini`, `ollama` |
| `LLM_MODEL` | *blank* | Model identifier (provider-specific) |
| `LLM_BASE_URL` | *blank* | Override API endpoint |

No keys are embedded in the repository. Errors from LLM calls are
redacted before logging.

## Security

- **Demo mode** (R1): binds to `127.0.0.1`, no authentication,
  `DEMO_MODE=true`. Refuses to start when `APP_ENV=production`.
- **OIDC** (R2, planned): Keycloak authorization-code flow with state +
  nonce + PKCE, token signature / issuer / audience validation.
- **No hardcoded bypasses**: when `DEMO_MODE=false`, all data endpoints
  return 401 until OIDC is configured.
- **Secrets**: see `.env.example`. Never commit `.env`.

## SSO / SAML setup (Keycloak, R2)

The realm import at `keycloak-realm.json` defines:

- A confidential OIDC client `lumen-studio`.
- Roles: `viewer`, `analyst`, `admin`.

To start with Keycloak:

```bash
KEYCLOAK_ADMIN_PASSWORD=change-me docker compose --profile auth up --build
```

**SAML identity brokering** (e.g. Okta, Azure AD as upstream IdP):

1. Place the upstream IdP's SAML metadata XML at
   `http://path-to-idp-metadata.xml` or host it locally.
2. In the Keycloak admin console (`http://localhost:8080`), navigate to
   **Realm Settings → Identity Providers → Add identity provider → SAML**.
3. Upload the IdP metadata URL or XML.
4. Configure the SAML attribute mapping so the IdP's username/email
   map to Keycloak user attributes.
5. Set `KEYCLOAK_REALM=lumen-studio` and `OIDC_AUDIENCE=lumen-studio`
   in the backend environment so tokens validate against the correct
   audience.

---

Ryan Vo | AI & Machine Learning · <ryandtvo@gmail.com>