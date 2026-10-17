# API Reference

All endpoints are under `/api/v1/`. In demo mode, no authentication is
required. In production, a Bearer token issued by Keycloak is expected.

## Health

### `GET /api/v1/health`

Liveness probe — no authentication required.

**Response** `200 OK`
```json
{
  "status": "ok",
  "service": "lumen-studio"
}
```

### `GET /api/v1/version`

Runtime configuration summary (no secrets).

**Response** `200 OK`
```json
{
  "version": "1.0.0",
  "env": "development",
  "demo_mode": true
}
```

## Vtables

### `POST /api/v1/vtables`

Create a vtable definition.

**Request body**
| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Label, e.g. `MyClass::vtable` |
| `field_name` | string | yes | Identifier in decompiled code |
| `base_address` | string | no | Optional hex address |
| `slots` | `(string\|null)[]` | yes | Ordered function names; `null` = empty slot |

**Response** `201 Created`
```json
{
  "id": 1,
  "name": "MyClass::vtable",
  "field_name": "vtable",
  "base_address": "0x401000",
  "slots": ["fn_getType", "fn_addRef", null, "fn_method3"],
  "created_at": "2025-01-01T12:00:00+00:00",
  "updated_at": "2025-01-01T12:00:00+00:00"
}
```

### `GET /api/v1/vtables`

List vtables with pagination.

**Query parameters**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Offset |
| `limit` | integer | 50 | Page size (max 200) |

**Response** `200 OK` — array of Vtable objects.

### `GET /api/v1/vtables/{vtable_id}`

Retrieve a single vtable.

**Response** `200 OK` — Vtable object, or `404 Not Found`.

### `DELETE /api/v1/vtables/{vtable_id}`

Delete a vtable. Cascades to its resolutions.

**Response** `204 No Content` or `404 Not Found`.

## Resolutions

### `POST /api/v1/resolutions`

Resolve indirect calls in a code snippet against a vtable.

**Request body**
| Field | Type | Required | Description |
|---|---|---|---|
| `vtable_id` | integer | yes | Must exist |
| `code` | string | yes | Decompiled C snippet (max 65 536 chars) |

**Response** `201 Created`
```json
{
  "id": 1,
  "vtable_id": 1,
  "vtable_name": "MyClass::vtable",
  "code": "(*this->vtable[0])(arg);",
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

**Error** `404 Not Found` — vtable not found.

### `GET /api/v1/resolutions`

List past resolutions (summary view).

**Response** `200 OK`
```json
[
  {
    "id": 1,
    "vtable_id": 1,
    "vtable_name": "MyClass::vtable",
    "match_count": 3,
    "created_at": "2025-01-01T12:00:00+00:00"
  }
]
```

### `GET /api/v1/resolutions/{resolution_id}`

Retrieve a full resolution with all matches.

**Response** `200 OK` — Resolution object, or `404 Not Found`.