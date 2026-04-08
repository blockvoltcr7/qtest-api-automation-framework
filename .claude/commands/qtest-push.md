---
name: qtest-push
description: Push test cases to qTest Manager via the REST API. Use when the user says things like "push these test cases to qTest", "add test cases to qTest", "create test cases in qTest", "sync test cases to a module", "upload test cases to qTest", "push my tests to qTest module", or any variation of creating/uploading/syncing test cases into a qTest project folder. Handles both single test case creation and bulk collection creation. Requires a qTest Bearer token and project ID.
---

# qTest Push

Push one or many test cases into a qTest Manager module (folder) via the REST API.

## Decision: Single vs Bulk

| Scenario | Mode | Endpoint |
|---|---|---|
| User provides one test case | **Single** | `POST /api/v3/projects/{projectId}/test-cases` |
| User provides a list/file/array of test cases | **Bulk** | `POST /api/v3/projects/{projectId}/auto-test-logs?type=automation` |

## Step 1: Gather Required Inputs

Ask the user for any missing values before proceeding:

- **`QTEST_BASE_URL`** — e.g., `https://mycompany.qtestnet.com`
- **`QTEST_BEARER_TOKEN`** — Bearer token from qTest UI or `.env` file
- **`PROJECT_ID`** — numeric project ID
- **`MODULE_ID`** or **module name path** — where to place the test cases

Check for a `.env` file in the project first (`smoke_tests/.env` or `.env`). If `QTEST_BEARER_TOKEN` and `QTEST_PROJECT_ID` are present, use them automatically without asking.

## Step 2: Resolve the Target Module

If the user gave a module name (not a numeric ID), call the modules API to find it:

```
GET {QTEST_BASE_URL}/api/v3/projects/{PROJECT_ID}/modules?expand=descendants
Authorization: Bearer {QTEST_BEARER_TOKEN}
```

Search the returned tree for the module by name. Extract its numeric `id`. If ambiguous (multiple modules with same name), show the list and ask the user to confirm.

See [.claude/skills/qtest-push/references/modules-api.md](.claude/skills/qtest-push/references/modules-api.md) for the full modules API schema.

## Step 3a: Single Test Case

Use when pushing one test case. See [.claude/skills/qtest-push/references/single-test-case.md](.claude/skills/qtest-push/references/single-test-case.md) for the full schema.

**Minimum required body:**
```json
{
  "name": "<test case name>",
  "parent_id": <module_id>,
  "properties": [],
  "test_steps": [
    { "description": "<step>", "expected": "<expected result>", "order": 1 }
  ]
}
```

**Call:**
```
POST {QTEST_BASE_URL}/api/v3/projects/{PROJECT_ID}/test-cases?parentId={MODULE_ID}
Authorization: Bearer {QTEST_BEARER_TOKEN}
Content-Type: application/json
```

On `201 Created`, report back: test case name, `pid` (e.g. `TC-412`), and `web_url`.

## Step 3b: Bulk Test Cases

Use when pushing multiple test cases. See [.claude/skills/qtest-push/references/bulk-test-cases.md](.claude/skills/qtest-push/references/bulk-test-cases.md) for the full schema and polling instructions.

**Key rules:**
- Each test case needs a unique `automation_content` string (use name-based slug if not provided: e.g., `"project.module.TestCaseName"`)
- Use `module_names: ["<folder name>"]` per entry to target the module by name, OR set `parent_module` at the top level by PID (e.g., `"MD-8"`)
- `test_cycle` is required — ask the user for a Test Cycle PID (e.g., `"CL-1"`), or use a default "API Import" cycle if one exists

**Call:**
```
POST {QTEST_BASE_URL}/api/v3/projects/{PROJECT_ID}/auto-test-logs?type=automation
Authorization: Bearer {QTEST_BEARER_TOKEN}
Content-Type: application/json
```

This is **asynchronous** — poll the returned job ID:
```
GET {QTEST_BASE_URL}/api/v3/projects/queue-processing/{jobId}
```
Poll every 3 seconds until `state` is `"SUCCESS"` or `"FAILED"`. Report the final state.

## Error Handling

| Error | Likely Cause | Action |
|---|---|---|
| `401 Unauthorized` | Expired or invalid token | Ask user to regenerate token from qTest UI → Profile → API Access Tokens |
| `403 Forbidden` | User lacks project access | Confirm project ID and user role in qTest |
| `404 Not Found` | Bad project ID or module ID | Re-run module discovery in Step 2 |
| `400 Bad Request` | Missing `name`, `properties`, or malformed JSON | Show the validation error and fix the payload |
| Job state `"FAILED"` (bulk) | Payload issue or server error | Show the `message` field from the poll response |

## Output

After a successful push, always report:
- Number of test cases created
- Module they were placed in (name + ID)
- For single: the `pid` and `web_url`
- For bulk: the job ID and final state
