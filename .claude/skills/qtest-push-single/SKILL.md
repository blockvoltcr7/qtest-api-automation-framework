---
name: qtest-push-single
description: Push a single test case to a qTest Manager module (folder) via the REST API. Use when the user says "push this test case to qTest", "add a test case to qTest", "create a test case in qTest module", "upload one test case to qTest", or any variation of creating/adding a single test case into a qTest project folder. Reads credentials from the project root .env file automatically.
---

# qTest Push — Single Test Case

Push one test case into a qTest Manager module via `POST /api/v3/projects/{projectId}/test-cases`.

## Step 1: Load Credentials from .env

Read the `.env` file at the **project root** before anything else:

```
QTEST_DOMAIN=mycompany
QTEST_BEARER_TOKEN=eyJhbGci...
QTEST_PROJECT_ID=12345
```

Construct the base URL as `https://{QTEST_DOMAIN}.qtestnet.com`.
If any values are missing, ask the user before proceeding. Do not continue with empty credentials.

## Step 2: Resolve Target Module

If the user gave a module name (not a numeric ID), call the modules API:

```
GET {QTEST_BASE_URL}/api/v3/projects/{QTEST_PROJECT_ID}/modules?expand=descendants
Authorization: Bearer {QTEST_BEARER_TOKEN}
```

Walk the tree to find the module by name. Extract its numeric `id`.
If multiple modules share the same name, list them with `pid` and `parent_id` and ask the user to confirm.

See [references/modules-api.md](references/modules-api.md) for the full response schema.

## Step 3: Build the Request Body

Construct the JSON payload from what the user provided.

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Test case display name |
| `properties` | Yes | Pass `[]` if no custom fields needed |
| `parent_id` | Recommended | Numeric module ID from Step 2 |
| `test_steps` | No | Array of `{description, expected, order}` |

See [references/single-test-case-schema.md](references/single-test-case-schema.md) for the full schema and all optional fields.

## Step 4: Call the API

```
POST {QTEST_BASE_URL}/api/v3/projects/{QTEST_PROJECT_ID}/test-cases?parentId={MODULE_ID}
Authorization: Bearer {QTEST_BEARER_TOKEN}
Content-Type: application/json
```

Use the Bash tool with curl to execute the request.

## Step 5: Report Result

On `201 Created`, report:
- Test case name and `pid` (e.g. `TC-412`)
- `web_url` — direct link to open in qTest UI
- Module name and ID it was placed in

## Error Handling

| HTTP | Cause | Action |
|---|---|---|
| `401` | Expired/invalid token | Ask user to regenerate from qTest UI → Profile → API Access Tokens, update `.env` |
| `403` | No project access | Confirm `QTEST_PROJECT_ID` and user role in qTest |
| `404` | Invalid project or module ID | Re-run module lookup in Step 2 |
| `400` | Missing `name`/`properties` or bad JSON | Show the error detail and fix the payload |
