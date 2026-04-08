# Bulk Test Cases — Full API Schema

## Endpoint A (Recommended)

```
POST /api/v3/projects/{projectId}/auto-test-logs?type=automation
```

## Endpoint B (Legacy — global module targeting)

```
POST /api/v3.1/projects/{projectId}/test-runs/0/auto-test-logs?type=automation
```

> The `0` in the path is always literal — not a real run ID.

## Required Query Parameter

| Param | Value |
|---|---|
| `type` | `"automation"` |

## Request Body

```json
{
  "test_cycle": "CL-1",
  "parent_module": "MD-8",
  "execution_date": "2026-04-08T10:00:00Z",
  "build_number": "string",
  "build_url": "string",
  "test_logs": [
    {
      "name": "string",
      "automation_content": "unique.fingerprint.per.test.case",
      "status": "PASSED",
      "exe_start_date": "2026-04-08T10:00:00Z",
      "exe_end_date": "2026-04-08T10:00:30Z",
      "module_names": ["ParentFolder", "ChildFolder"],
      "note": "string",
      "properties": [],
      "test_step_logs": [
        {
          "description": "string",
          "expected_result": "string",
          "actual_result": "string",
          "status": "PASSED",
          "order": 1
        }
      ]
    }
  ]
}
```

## Top-Level Required Fields

| Field | Notes |
|---|---|
| `test_cycle` | Test Cycle PID e.g. `"CL-1"` — required even for creation-only use |
| `execution_date` | ISO 8601 datetime — use current time if not specified |
| `test_logs` | One entry per test case |

## Per-Test-Log Required Fields

| Field | Notes |
|---|---|
| `name` | Test case display name |
| `automation_content` | Unique fingerprint per test case — deduplication key |
| `status` | See status values below |
| `exe_start_date` | ISO 8601 — use `execution_date` if not specified |
| `exe_end_date` | ISO 8601 — use `execution_date` if not specified |

## Status Values

`PASSED` · `FAILED` · `SKIPPED` · `BLOCKED` · `INCOMPLETE` · `UNEXECUTED`

Use `UNEXECUTED` when creating test cases without recording a result.

## Module Targeting

| Approach | Field | Where | Format |
|---|---|---|---|
| By folder name (per test case) | `module_names` | Inside each `test_log` | `["Parent", "Child"]` — creates path if missing |
| By module PID (global, Endpoint B) | `parent_module` | Top-level body | `"MD-8"` or numeric ID string |

## Async Response — 200 OK

```json
{ "id": 88001234, "state": "QUEUED" }
```

## Polling

```
GET /api/v3/projects/queue-processing/{jobId}
Authorization: Bearer {token}
```

Poll every 3 seconds. States: `QUEUED` → `IN_PROGRESS` → `SUCCESS` or `FAILED`.

## Batch Size

Keep under **500 test logs** per request. Split into multiple requests for larger suites.

## Minimal curl Example

```bash
curl -s -X POST \
  "https://${QTEST_DOMAIN}.qtestnet.com/api/v3/projects/${QTEST_PROJECT_ID}/auto-test-logs?type=automation" \
  -H "Authorization: Bearer ${QTEST_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "test_cycle": "CL-1",
    "execution_date": "2026-04-08T10:00:00Z",
    "test_logs": [
      {
        "name": "Verify login with valid credentials",
        "automation_content": "auth.login.ValidCredentials",
        "status": "UNEXECUTED",
        "exe_start_date": "2026-04-08T10:00:00Z",
        "exe_end_date": "2026-04-08T10:00:00Z",
        "module_names": ["Authentication", "Login"]
      }
    ]
  }'
```
