# Phase 1: Authenticate

## Purpose

Establish an authenticated `requests.Session` that all subsequent phases use to call the qTest API. This phase reuses existing code from `smoke_tests/config.py` with zero modifications.

---

## What Happens

1. Call `validate_config()` to verify that all required environment variables are present.
2. Call `create_session()` to create a `requests.Session` pre-configured with authentication headers.
3. Return the session for use by Phases 2-4.

---

## Input

Environment variables loaded from `.env` (via `python-dotenv`):

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `QTEST_DOMAIN` | Yes (unless `QTEST_BASE_URL` set) | Subdomain, e.g., `mycompany` for `mycompany.qtestnet.com` |
| `QTEST_BASE_URL` | Alternative to DOMAIN | Full base URL if non-standard (e.g., on-prem) |
| `QTEST_BEARER_TOKEN` | Yes (unless username/password set) | Pre-generated API token from qTest |
| `QTEST_USERNAME` | Alternative to bearer token | Username for OAuth login |
| `QTEST_PASSWORD` | Alternative to bearer token | Password for OAuth login |
| `QTEST_PROJECT_ID` | Yes | Numeric project ID |

---

## Output

An authenticated `requests.Session` object with:
- `Content-Type: application/json` header
- `Accept: application/json` header
- `Authorization: Bearer <token>` header

---

## Two Authentication Methods

### Method A: Bearer Token (preferred)

When `QTEST_BEARER_TOKEN` is set, the token is injected directly into the session headers. No API call is made.

```python
# From config.py lines 74-76
if QTEST_BEARER_TOKEN:
    session.headers["Authorization"] = f"Bearer {QTEST_BEARER_TOKEN}"
    return session
```

This is the preferred method because:
- No network call during authentication
- Token can be long-lived (configured in qTest admin)
- Simpler to manage in CI/CD environments

### Method B: Username/Password OAuth

When no bearer token is set but `QTEST_USERNAME` and `QTEST_PASSWORD` are provided, the session authenticates via the qTest OAuth endpoint.

```python
# From config.py lines 79-96
login_url = f"{QTEST_BASE_URL}/oauth/token"
login_payload = {
    "grant_type": "password",
    "username": QTEST_USERNAME,
    "password": QTEST_PASSWORD,
}
login_headers = {"Content-Type": "application/x-www-form-urlencoded"}

resp = session.post(login_url, data=login_payload, headers=login_headers)
resp.raise_for_status()
token = resp.json().get("access_token")
```

Note: The OAuth endpoint uses `application/x-www-form-urlencoded`, not JSON. The session's default `Content-Type` is temporarily overridden for this call via the explicit `headers` parameter.

---

## Code Reference

**File**: `smoke_tests/config.py`

### `validate_config()` (lines 34-53)

Checks three conditions:
1. `QTEST_BASE_URL` is non-empty (derived from `QTEST_DOMAIN` or set directly)
2. Either `QTEST_BEARER_TOKEN` is set, or both `QTEST_USERNAME` and `QTEST_PASSWORD` are set
3. `QTEST_PROJECT_ID` is set

If any check fails, prints a clear error message and calls `sys.exit(1)`.

### `create_session()` (lines 61-96)

Creates the session, tries Bearer token first, falls back to OAuth. Returns the ready-to-use session.

### `get_api_base()` (lines 56-58)

Returns the fully-qualified API v3 project base URL:
```
https://{domain}.qtestnet.com/api/v3/projects/{projectId}
```

---

## No New Code Needed

Phase 1 is a direct reuse of `config.py`. The pipeline script simply calls:

```python
from config import validate_config, create_session, get_api_base

validate_config()
session = create_session()
api_base = get_api_base()
```

---

## Failure Mode

Phase 1 failures are always fatal. There is no way to proceed without authentication.

| Failure | Cause | Behavior |
|---------|-------|----------|
| Missing `QTEST_DOMAIN` | `.env` not configured | `sys.exit(1)` with message listing missing values |
| Missing auth credentials | Neither token nor username/password set | `sys.exit(1)` with message |
| Missing `QTEST_PROJECT_ID` | `.env` incomplete | `sys.exit(1)` with message |
| OAuth login fails | Bad credentials or network error | `raise_for_status()` raises `HTTPError`, script exits |
| OAuth returns no token | Unexpected response format | `sys.exit(1)` with response body printed |

All error messages direct the user to check the `.env` file. The script prints:

```
============================================================
CONFIGURATION ERROR -- check your .env file
============================================================
  - QTEST_DOMAIN or QTEST_BASE_URL must be set
  - QTEST_PROJECT_ID must be set

Copy .env.example to .env and fill in your values.
```
