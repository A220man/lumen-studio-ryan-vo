# Changelog

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added (this checkpoint)
- `base_address` field in resolution responses (`ResolutionResponse` schema)
- Resolution create/get endpoints now include the vtable's base address
- Frontend API client types updated to include `base_address`
- Test assertions for base_address in resolution workflow tests

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to Lumen Studio are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2025-01-01

### Added
- FastAPI backend with SQLite persistence (vtable definitions, resolutions).
- Deterministic vtable resolver: parses `FIELD[INDEX]` indirection
  patterns in decompiled C snippets and maps integer indices to function
  names from user-defined slot layouts.
- Vtable CRUD API (`POST/GET/DELETE /api/v1/vtables`).
- Resolution workflow API (`POST /api/v1/resolutions`, `GET /api/v1/resolutions`,
  `GET /api/v1/resolutions/{id}`).
- React + Vite frontend with typed API client, vtable definition form,
  resolver panel, and results list with JSON export.
- Health check and version endpoints.
- Dockerfiles (nonroot) and compose.yaml (app + Keycloak profile).
- CI workflow (pytest, vite build/test, docker buildx).
- README with install/run/test instructions, architecture diagram,
  API reference, and AI/ML evaluation notes.

### Known limitations (R1)
- Local-only demo mode; OIDC/Keycloak PKCE auth planned for R2.
- LLM advisory explanations planned for R2 (OpenAI/Anthropic/Gemini adapters).
- Only literal-integer vtable indices are resolved (no variable or
  expression indices).
- Switch/jump-table recognition beyond `FIELD[INDEX]` is deferred.

## [1.0.1] — 2025-10-23

### Added
- Hexadecimal index support in vtable resolver: `vtable[0x6]`, `vtable[0X10]`
  patterns are now recognized and resolved alongside decimal indices.
- New engine tests for hex indices (lowercase `0x` and uppercase `0X`).

### Changed
- Updated pattern regex to match both decimal and hex integer indices
  (case-insensitive `0x` prefix).