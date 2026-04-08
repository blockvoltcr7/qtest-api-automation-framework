---
name: qtest-push-bulk
description: Push a collection of test cases to a qTest Manager module (folder) via the REST API. Use when the user says "push these test cases to qTest", "bulk upload test cases to qTest", "add multiple test cases to qTest", "push a collection of tests to qTest module", "sync test suite to qTest", or any variation of creating/uploading multiple test cases at once into a qTest project folder. Reads credentials from the project root .env file automatically.
---

# qTest Push — Bulk Test Cases

Push a collection of test cases into a qTest Manager module via the automation test logs endpoint.
Test cases are created as a side effect of submitting automation results — this is the official qTest bulk creation pattern.

## Step 1: Load Credentials from .env

Read the `.env` file at the **project root** before anything else:

```
QTEST_DOMAIN=mycompany.qtestnet.com
QTEST_BEARER_TOKEN=eyJhbGci...
QTEST_PROJECT_ID=12345
```

Construct the base URL as `https://{QTEST_DOMAIN}`.
If any values are missing, ask the user before proceeding. Do not continue with empty credentials.

## Step 2: Resolve Target Module

If the user gave a module name (not a PID or numeric ID), call the modules API:

```
GET {QTEST_BASE_URL}/api/v3/projects/{QTEST_PROJECT_ID}/modules?expand=descendants
Authorization: Bearer {QTEST_BEARER_TOKEN}
```

Capture the module's `id` (integer) and `pid` (e.g. `"MD-8"`).

See [references/modules-api.md](references/modules-api.md) for the full response schema.

## Step 3: Get Test Cycle

`test_cycle` (PID e.g. `"CL-1"`) is required by the endpoint even for pure test case creation.
Ask the user if not provided. If they don't have one, suggest creating a dedicated "API Import" cycle in qTest Test Execution first.

## Step 4: Build the Request Body

One `test_log` entry per test case. Key rules:
- Each entry needs a unique `automation_content` fingerprint. Generate as `"project.module.TestCaseName"` if not provided by the user.
- Use `module_names: ["<folder name>"]` per entry to target the module by name.
- Use `status: "UNEXECUTED"` when you only want to create the test case without recording a pass/fail result.

See [references/bulk-test-cases-schema.md](references/bulk-test-cases-schema.md) for the full schema, all fields, status values, and both endpoint variants.

## Step 5: Call the API (Async)

```
POST {QTEST_BASE_URL}/api/v3/projects/{QTEST_PROJECT_ID}/auto-test-logs?type=automation
Authorization: Bearer {QTEST_BEARER_TOKEN}
Content-Type: application/json
```

Use the Bash tool with curl. The response returns a job ID — processing is asynchronous.

## Step 6: Poll Until Complete

```
GET {QTEST_BASE_URL}/api/v3/projects/queue-processing/{jobId}
Authorization: Bearer {QTEST_BEARER_TOKEN}
```

Poll every 3 seconds until `state` is `"SUCCESS"` or `"FAILED"`. Show the user a status update while waiting.

## Step 7: Report Result

On `SUCCESS`, report:
- Number of test cases created/updated
- Module they were placed in (name + ID)
- Job ID for traceability

On `FAILED`, show the `message` field from the poll response.

## Idempotency

`automation_content` is the deduplication key. Re-running with the same values updates the existing test case — it does not create a duplicate. Safe to run from CI pipelines repeatedly.

## Error Handling

| HTTP | Cause | Action |
|---|---|---|
| `401` | Expired/invalid token | Ask user to regenerate, update `.env` |
| `403` | No project access | Confirm `QTEST_PROJECT_ID` and user role |
| `400` | Missing `test_cycle`, `execution_date`, or `test_logs` | Check required fields against schema |
| `413` | Payload too large | Split into batches of fewer than 500 test logs |
| Job `FAILED` | Processing error | Read `message` from poll response |
