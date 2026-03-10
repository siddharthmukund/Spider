# Phase 3 Design: Platform Modernization

This document outlines the design approach for Phase 3 of the SEO Crawler enhancement plan, focused on modernizing the platform with multi-tenant authentication, advanced rate limiting, centralized logging, SSRF enhancements and a security dashboard.

## 1. Multi‑Tenant Authentication

### Goals

- Support multiple users/clients with independent credentials
- Allow revocation, rotation, and scoped access
- Provide both interactive (OAuth2) and machine (API key/JWT) flows
- Replace the single `WEBAPP_API_KEY` mechanism with a flexible system

### Components

1. **User database** – simple SQLite table `users` with columns:
   - `id` (uuid)
   - `username` (unique)
   - `hashed_password` (bcrypt)
   - `email` (optional)
   - `scopes` (json list)
   - `is_active`, `is_superuser`
   - `api_keys` (one-to-many table for service keys)

2. **Password hashing** – use `passlib` `bcrypt` or `argon2`
3. **JWT tokens** – issued on login with expiry, signed with secret (`JWT_SECRET` env)
   - Contains `sub` (user id), `scopes`, `exp`, `aud`, `iss`
4. **OAuth2 Password Grant** – `OAuth2PasswordBearer` dependency for endpoints
   - `/token` endpoint implementing standard flow
5. **API key fallback** – still support service-account keys stored per-user
   - Keys rotated independently, stored hashed and compared with `compare_digest`
6. **Role/Scope Enforcement** – protect endpoints with `Depends(get_current_user)` and scope checks
7. **Admin CLI** – utility script `scripts/manage_users.py` to create/list/revoke users and keys

### High‑Level Flow

1. Client obtains a JWT by POST `/token` with username/password.
2. Server authenticates against user table, verifies password, issues JWT.
3. Client includes `Authorization: Bearer <token>` header for protected endpoints.
4. For service-to-service, client may use API key header (fallback) or JWTs.
5. JWT middleware decodes token, verifies signature, expiry, audience, scopes, and returns user object.

### Implementation Steps

1. Add `users` and `api_keys` tables to `webapp/store.py` or a new `webapp/db.py` module.
2. Install dependencies: `passlib[bcrypt]`, `pyjwt`.
3. Extend `webapp/security/auth.py` to:
   - Provide `verify_token()` and `get_current_user()` deps.
   - Migrate existing `verify_api_key` to multi-key version referencing user records.
4. Add `/token` FastAPI route in `webapp/main.py`.
5. Update tests under `tests/api` for new authentication scenarios.
6. Provide migration script or instructions to convert single API key to a user record.

## 2. Advanced Rate Limiting

### Goals

- Allow per-user, per-tenant limits
- Geographic/IP-based adjustments
- Adaptive algorithms (increase/decrease based on error rates)
- Support the existing Redis backend and optional in-memory

### Design Notes

- Extend `RateLimiter` to key by user ID instead of client IP.
- Add middleware to resolve geographic location via remote address (use `geoip2` database).
- Add configuration for dynamic limits: e.g. `rates.json` with per-tenant tiers.

## 3. Centralized Logging

### Goals

- Stream audit logs and events to ELK/CloudWatch
- Replace file-based `audit.log` with a handler that writes to stdout (for Docker) and sends to external system.

### Approach

- Modify `AuditLogger` to support multiple handlers (file+stdout+HTTP)
- Use environment variable `AUDIT_BACKEND` (`file`, `stdout`, `elk`) and config `ELK_URL`
- Provide sample `docker-compose.elasticsearch.yml`

## 4. SSRF Enhancements

- Implement allowlist mode: environment variable `SSRF_ALLOWED_HOSTS` or `base_url` domain check.  The validator should also tolerate DNS resolution failures (useful for offline testing).
- Add caching of DNS resolutions to prevent TOCTOU.

## 5. Security Dashboard

### Endpoints

- `GET /admin/metrics` – returns rate-limit usage, login attempts, active tokens count
- `GET /admin/logs` – paginated audit events
- `POST /admin/users` – manage users (requires superuser scope)

### UI

- Minimal static React or serve pre-generated HTML from `webapp/static/dashboard.html`.

## Dependencies

- fastapi[all]
- passlib[bcrypt]
- pyjwt
- geoip2 (optional)
- elasticsearch or opensearch-py

## Next Steps

Proceed sequentially:
1. Add database layer and user models.
2. Implement token issuance & validation.
3. Update existing endpoints to use new auth.
4. Expand rate limiter and audit logger accordingly.
5. Write tests for each new capability.
6. Update docs and release notes.

---

This design will guide development; each section below will be turned into actionable commits.