# Bulk Test Cases API Reference

## Endpoint (Recommended — Endpoint A)

```
POST /api/v3/projects/{projectId}/auto-test-logs?type=automation
```

> **Legacy Endpoint B** (when you need to target module by PID globally):
> `POST /api/v3.1/projects/{projectId}/test-runs/0/auto-test-logs?type=automation`
> The `0` in the path is literal — always use `0`.

## Query Parameters

| Parameter | Value | Required |
|---|---|---|
| `type` | `"automation"` | Yes |

## Request Body Schema

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

### Top-Level Required Fields

| Field | Type | Notes |
|---|---|---|
| `test_cycle` | string | Test Cycle ID or PID (e.g. `"CL-1"`). Required even if you only care about creating test cases. |
| `execution_date` | ISO 8601 string | Use current datetime if not specified by user |
| `test_logs` | array | One entry per test case |

### Per-Test-Log Required Fields

| Field | Type | Notes |
|---|---|---|
| `name` | string | Test case display name |
| `automation_content` | string | **Deduplication key** — must be unique per test case. If not provided by user, generate as `"project.module.TestCaseName"` using the test case name. Same content on re-submission = update, not duplicate. |
| `status` | string | `PASSED`, `FAILED`, `SKIPPED`, `BLOCKED`, `INCOMPLETE`, `UNEXECUTED` |
| `exe_start_date` | ISO 8601 | Use `execution_date` value if not specified |
| `exe_end_date` | ISO 8601 | Use `execution_date` value if not specified |

### Module Targeting

| Approach | Field | Where | Format |
|---|---|---|---|
| By folder name (per test case) | `module_names` | Inside each `test_log` | `["Parent", "Child"]` — creates path if missing |
| By module PID (global, Endpoint B) | `parent_module` | Top-level body | `"MD-8"` or numeric ID string |

Use `module_names` (Endpoint A) when different test cases go into different folders, or when you only have the folder name (not PID).

## Response — 200 OK (Async)

```json
{
  "id": 88001234,
  "state": "QUEUED"
}
```

## Polling for Completion

```
GET /api/v3/projects/queue-processing/{jobId}
Authorization: Bearer {token}
```

Poll every 3 seconds until `state` is `"SUCCESS"` or `"FAILED"`.

```json
{
  "id": 88001234,
  "state": "SUCCESS",
  "message": "Test log submitted successfully"
}
```

| State | Meaning |
|---|---|
| `QUEUED` | Waiting to process |
| `IN_PROGRESS` | Currently running |
| `SUCCESS` | All test cases created/updated |
| `FAILED` | Check `message` field for details |

## Batch Size Guidance

Keep payloads under **500 test logs** per request. The API returns `413` on oversized payloads — split into multiple requests if needed.

## Idempotency

`automation_content` is the dedup key. Re-submitting the same value:
- Does **not** create a duplicate test case
- Records a new execution result on the existing test case

This makes bulk push safe to run repeatedly (e.g., on every CI run).

## Error Codes

| Code | Cause |
|---|---|
| 400 | Missing `test_cycle`, `execution_date`, or `test_logs`; invalid status value |
| 401 | Expired or missing Bearer token |
| 403 | No project access |
| 404 | `projectId` not found |
| 413 | Payload too large — split into smaller batches |
