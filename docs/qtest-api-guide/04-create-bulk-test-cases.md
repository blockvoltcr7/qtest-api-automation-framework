# Create a Collection of Test Cases (Bulk)

qTest Manager does not expose a direct endpoint that accepts an array of test case objects for batch creation. Instead, bulk test case creation is achieved through the **Automation Test Logs** endpoint, which creates test cases as a side effect of submitting automation results.

This is the official supported pattern for populating a module with multiple test cases in a single API call.

---

## How It Works

When you submit automation test results, qTest:

1. Looks up each test case by its `automation_content` fingerprint (a unique string identifier you assign).
2. **Creates** the test case if no match exists.
3. **Reuses** the existing test case if a match is found (idempotent by design — safe to re-run).
4. Records the execution result (pass/fail/etc.) against each test case.

This means: submitting test logs is the mechanism for both **creating** and **executing** test cases in bulk.

---

## Endpoint

There are two variants. **Endpoint A** (extended) is recommended for new integrations because it supports per-test-case module hierarchy via `module_names`.

### Endpoint A (Recommended)

```
POST /api/v3/projects/{projectId}/auto-test-logs?type=automation
```

**Full URL:**
```
https://{your-qtest-domain}/api/v3/projects/{projectId}/auto-test-logs?type=automation
```

### Endpoint B (Original / Legacy)

```
POST /api/v3.1/projects/{projectId}/test-runs/0/auto-test-logs?type=automation
```

> **Note:** The `testRunId` path segment must always be `0` (zero) when using this endpoint for bulk creation. This is a fixed value in the API contract, not a real run ID.

---

## Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `projectId` | integer (int64) | Yes | Numeric ID of the qTest project |

## Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `type` | string | Yes | Must be `"automation"` |

---

## Request Headers

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## Request Body Schema — `AutomationRequest`

```json
{
  "test_cycle": "string",
  "parent_module": "string",
  "execution_date": "string",
  "build_number": "string",
  "build_url": "string",
  "test_logs": [
    {
      "name": "string",
      "automation_content": "string",
      "status": "string",
      "exe_start_date": "string",
      "exe_end_date": "string",
      "module_names": ["string"],
      "note": "string",
      "attachments": [],
      "properties": [],
      "test_step_logs": [
        {
          "description": "string",
          "expected_result": "string",
          "actual_result": "string",
          "status": "string",
          "order": 0,
          "attachments": []
        }
      ]
    }
  ]
}
```

---

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `test_cycle` | string | Yes | The ID or PID of the Test Cycle to record results under (e.g., `"CL-1"` or the numeric ID). |
| `execution_date` | string (ISO 8601) | Yes | The date/time of test execution. Format: `"2026-04-08T10:00:00Z"` |
| `test_logs` | array of `TestLogResource` | Yes | The collection of test case results to submit. One object per test case. |
| `parent_module` | string | No | **(Endpoint B only)** The ID or PID (e.g., `"MD-8"`) of the destination module for all test cases in this request. Acts as a global default for all `test_logs` when `module_names` is not used. |
| `build_number` | string | No | CI build number for traceability (e.g., `"build-142"`) |
| `build_url` | string | No | URL to the CI build for traceability |

---

### `TestLogResource` — Per-Test-Case Entry

Each object in `test_logs` represents one test case and its execution result.

```json
{
  "name": "Verify login with valid credentials",
  "automation_content": "com.example.tests.auth.LoginTest#testValidLogin",
  "status": "PASSED",
  "exe_start_date": "2026-04-08T10:00:00Z",
  "exe_end_date": "2026-04-08T10:00:45Z",
  "module_names": ["Authentication", "Login"],
  "note": "Ran against staging environment",
  "test_step_logs": [
    {
      "description": "Navigate to login page",
      "expected_result": "Login form is displayed",
      "actual_result": "Login form is displayed",
      "status": "PASSED",
      "order": 1
    }
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | The test case name. Used as the display name when a new test case is created. |
| `automation_content` | string | Yes | **Unique fingerprint** for this test case. qTest uses this to match submissions to existing test cases and avoid duplicates. Use a stable, unique identifier such as a fully-qualified class + method name, or a UUID. |
| `status` | string | Yes | Execution result. See [Status Values](#status-values) below. |
| `exe_start_date` | string (ISO 8601) | Yes | When execution of this test case began |
| `exe_end_date` | string (ISO 8601) | Yes | When execution of this test case ended |
| `module_names` | array of strings | No | **(Endpoint A only)** Ordered folder path for placing this test case. `["Parent", "Child"]` resolves to the `Child` folder inside `Parent`. If the path does not exist, qTest creates the intermediate folders. Takes precedence over `parent_module`. |
| `note` | string | No | Free-text notes attached to the test run result |
| `attachments` | array | No | File attachments for the test run result |
| `properties` | array of `PropertyResource` | No | Custom field values for the test case. Same schema as in the single test case endpoint. |
| `test_step_logs` | array of `TestStepLogResource` | No | Execution results for individual test steps |

---

### Status Values

| Value | Meaning |
|---|---|
| `PASSED` | Test case passed |
| `FAILED` | Test case failed |
| `SKIPPED` | Test case was skipped |
| `BLOCKED` | Test case was blocked |
| `INCOMPLETE` | Test case is incomplete |
| `UNEXECUTED` | Not yet executed (creates the test case without a result) |

---

### `TestStepLogResource` — Per-Step Results

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | string | Yes | The step action/instruction |
| `expected_result` | string | Yes | What the step expected to observe |
| `actual_result` | string | Yes | What was actually observed during execution |
| `status` | string | Yes | Step result: `"PASSED"`, `"FAILED"`, `"SKIPPED"`, `"BLOCKED"` |
| `order` | integer | Yes | Step sequence number (1-based) |
| `attachments` | array | No | Screenshots or files attached to this step result |

---

## Module Placement: Endpoint A vs Endpoint B

| Approach | Endpoint | Field | Format | Behavior |
|---|---|---|---|---|
| By name (per test case) | Endpoint A | `module_names` in each `test_log` | `["Parent", "Child"]` | Creates folder hierarchy by name if needed. Each test case can target a different folder. |
| By ID/PID (global) | Endpoint B | `parent_module` at top level | `"MD-8"` or `"2107619"` | All test cases in the request go to this one folder. Cannot be varied per test case. |

---

## Asynchronous Processing

Both endpoints process submissions **asynchronously**. The immediate response returns a job ID, not the created test cases.

### Submission Response — `200 OK`

```json
{
  "id": 88001234,
  "state": "QUEUED"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Job queue ID — use this to poll for completion |
| `state` | string | Initial state: `"QUEUED"` |

---

### Poll for Completion

```
GET /api/v3/projects/queue-processing/{jobId}
```

```http
GET https://mycompany.qtestnet.com/api/v3/projects/queue-processing/88001234
Authorization: Bearer {access_token}
```

#### Poll Response

```json
{
  "id": 88001234,
  "state": "SUCCESS",
  "message": "Test log submitted successfully"
}
```

| `state` Value | Meaning |
|---|---|
| `QUEUED` | Job is waiting to be processed |
| `IN_PROGRESS` | Job is currently running |
| `SUCCESS` | All test cases created/updated successfully |
| `FAILED` | Processing failed — check `message` for details |

Poll every 2–5 seconds until `state` is `"SUCCESS"` or `"FAILED"`.

---

## Full Request Examples

### Endpoint A — Multiple Test Cases with Per-Case Module Targeting

```http
POST https://mycompany.qtestnet.com/api/v3/projects/12345/auto-test-logs?type=automation
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "test_cycle": "CL-1",
  "execution_date": "2026-04-08T10:00:00Z",
  "build_number": "build-221",
  "test_logs": [
    {
      "name": "Verify login with valid credentials",
      "automation_content": "com.example.auth.LoginTest#testValidLogin",
      "status": "PASSED",
      "exe_start_date": "2026-04-08T10:00:00Z",
      "exe_end_date": "2026-04-08T10:00:45Z",
      "module_names": ["Authentication", "Login"],
      "test_step_logs": [
        {
          "description": "Navigate to login page",
          "expected_result": "Login form is displayed",
          "actual_result": "Login form is displayed",
          "status": "PASSED",
          "order": 1
        },
        {
          "description": "Enter valid credentials and submit",
          "expected_result": "User is redirected to dashboard",
          "actual_result": "User is redirected to dashboard",
          "status": "PASSED",
          "order": 2
        }
      ]
    },
    {
      "name": "Verify login fails with invalid password",
      "automation_content": "com.example.auth.LoginTest#testInvalidPassword",
      "status": "PASSED",
      "exe_start_date": "2026-04-08T10:01:00Z",
      "exe_end_date": "2026-04-08T10:01:30Z",
      "module_names": ["Authentication", "Login"],
      "test_step_logs": [
        {
          "description": "Enter valid username and invalid password",
          "expected_result": "Error message is displayed",
          "actual_result": "Error message is displayed",
          "status": "PASSED",
          "order": 1
        }
      ]
    },
    {
      "name": "Verify user can reset password",
      "automation_content": "com.example.auth.PasswordResetTest#testResetFlow",
      "status": "FAILED",
      "exe_start_date": "2026-04-08T10:02:00Z",
      "exe_end_date": "2026-04-08T10:02:55Z",
      "module_names": ["Authentication", "Password Reset"],
      "test_step_logs": [
        {
          "description": "Click Forgot Password link",
          "expected_result": "Password reset page is displayed",
          "actual_result": "Password reset page is displayed",
          "status": "PASSED",
          "order": 1
        },
        {
          "description": "Submit registered email address",
          "expected_result": "Confirmation email is sent",
          "actual_result": "500 Internal Server Error",
          "status": "FAILED",
          "order": 2
        }
      ]
    }
  ]
}
```

---

### Endpoint B — All Test Cases into One Module (by PID)

```http
POST https://mycompany.qtestnet.com/api/v3.1/projects/12345/test-runs/0/auto-test-logs?type=automation
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "test_cycle": "CL-1",
  "parent_module": "MD-8",
  "execution_date": "2026-04-08T10:00:00Z",
  "test_logs": [
    {
      "name": "TC-001: Verify homepage loads",
      "automation_content": "com.example.smoke.HomepageTest#testLoad",
      "status": "PASSED",
      "exe_start_date": "2026-04-08T10:00:00Z",
      "exe_end_date": "2026-04-08T10:00:10Z",
      "test_step_logs": []
    },
    {
      "name": "TC-002: Verify navigation menu is present",
      "automation_content": "com.example.smoke.HomepageTest#testNavMenu",
      "status": "PASSED",
      "exe_start_date": "2026-04-08T10:00:11Z",
      "exe_end_date": "2026-04-08T10:00:20Z",
      "test_step_logs": []
    }
  ]
}
```

---

## Full curl Workflow with Polling

```bash
#!/bin/bash
TOKEN="eyJhbGciOiJSUzI1NiJ9..."
BASE_URL="https://mycompany.qtestnet.com"
PROJECT_ID=12345

# Step 1: Submit bulk test cases
RESPONSE=$(curl -s -X POST \
  "$BASE_URL/api/v3/projects/$PROJECT_ID/auto-test-logs?type=automation" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_cycle": "CL-1",
    "execution_date": "2026-04-08T10:00:00Z",
    "test_logs": [
      {
        "name": "Test Case One",
        "automation_content": "suite.TestOne",
        "status": "PASSED",
        "exe_start_date": "2026-04-08T10:00:00Z",
        "exe_end_date": "2026-04-08T10:00:30Z",
        "module_names": ["My Module"]
      }
    ]
  }')

JOB_ID=$(echo "$RESPONSE" | jq -r '.id')
echo "Job submitted: $JOB_ID"

# Step 2: Poll until complete
while true; do
  STATE=$(curl -s \
    "$BASE_URL/api/v3/projects/queue-processing/$JOB_ID" \
    -H "Authorization: Bearer $TOKEN" \
    | jq -r '.state')

  echo "Job state: $STATE"

  if [ "$STATE" = "SUCCESS" ] || [ "$STATE" = "FAILED" ]; then
    break
  fi

  sleep 3
done

echo "Final state: $STATE"
```

---

## Error Responses

| Status | Cause | Resolution |
|---|---|---|
| `400 Bad Request` | Missing required fields (`test_cycle`, `execution_date`, `test_logs`), invalid status value, or `testRunId` is not `0` on Endpoint B | Review the request body against the schema |
| `401 Unauthorized` | Missing or expired Bearer token | Re-authenticate |
| `403 Forbidden` | User does not have access to this project | Verify project membership |
| `404 Not Found` | `projectId` does not exist | Confirm project ID |
| `413 Payload Too Large` | Request body is too large | Split into multiple smaller batches (recommended: fewer than 500 test logs per request) |

---

## Important Notes

### Idempotency via `automation_content`

The `automation_content` field is the deduplication key. If you re-submit a request with the same `automation_content` for an existing test case:
- qTest **does not create a duplicate** test case.
- It records the new result as a new execution against the existing test case.
- This makes the endpoint safe to call on every CI run.

Choose a stable, unique string per test case — typically the fully-qualified test class and method name from your test framework.

### No Direct `parent_id` Field

Unlike the single test case endpoint, the bulk endpoint does not use `parent_id` (integer). Module targeting uses:
- **Endpoint A:** `module_names` (array of strings, per test log) — targets by folder name path
- **Endpoint B:** `parent_module` (string, top-level) — targets by module PID or ID for all test logs

### Batch Size Guidance

The API returns `413` on oversized payloads. No hard limit is published in the spec. As a practical guideline:
- Keep batches under **500 test logs** per request.
- For very large suites, chunk into multiple requests and track job IDs for each.

### Test Cycle Requirement

The `test_cycle` field is required. If your workflow is purely about creating test cases in Test Design (not recording execution results), you must still reference a valid Test Cycle. Create a dedicated "Bulk Import" test cycle in your project for this purpose.
