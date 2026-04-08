# Authentication

All qTest Manager API requests require a Bearer token in the `Authorization` header. Tokens are obtained by exchanging your qTest credentials against the token endpoint.

## Endpoint

```
POST https://{your-qtest-domain}/oauth/token
```

## Request

### Headers

```http
Content-Type: application/x-www-form-urlencoded
```

### Body (form-encoded)

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_type` | string | Yes | Must be `"password"` |
| `username` | string | Yes | Your qTest account email |
| `password` | string | Yes | Your qTest account password |

### Example

```http
POST https://mycompany.qtestnet.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=user@example.com&password=yourpassword
```

## Response

### Success — `200 OK`

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 36000,
  "scope": "read write"
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | string | The Bearer token to include in all subsequent API calls |
| `token_type` | string | Always `"bearer"` |
| `expires_in` | integer | Seconds until the token expires (typically 36000 = 10 hours) |
| `scope` | string | Granted OAuth scopes |

### Error — `401 Unauthorized`

```json
{
  "error": "invalid_grant",
  "error_description": "Bad credentials"
}
```

## Using the Token

Include the token in every API request:

```http
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
```

### Example (curl)

```bash
TOKEN=$(curl -s -X POST "https://mycompany.qtestnet.com/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&username=user@example.com&password=yourpassword" \
  | jq -r '.access_token')
```

## Notes

- Tokens expire after `expires_in` seconds. Re-authenticate when expired — the API returns `401` with `"error": "invalid_token"`.
- For CI/CD pipelines, store credentials in environment variables or a secrets manager. Never hardcode them in source files.
- qTest also supports API tokens generated from the UI under **Profile > API Access Tokens**, which do not expire and can be used as Bearer tokens directly.
