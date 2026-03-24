# Phase 4: Get Statuses & Failure Logs

This is the key new capability of the report pipeline. While Phases 1-3 and 5 reuse existing smoke test code nearly verbatim, Phase 4 introduces failure-log enrichment -- fetching detailed execution logs for every failed or blocked test run so the morning report can tell the team *why* things failed, not just *that* they failed.

---

## Overview

Phase 4 does three things:

1. **Fetch status definitions** -- build a lookup map from status ID to status name
2. **Resolve status for every run** -- using a 3-fallback strategy to handle qTest API inconsistencies
3. **Fetch failure details** -- for each failed/blocked run, call the test-logs endpoint to get step-level failure information

---

## API Call A: Get Execution Statuses

```
GET /api/v3/projects/{projectId}/test-runs/execution-statuses
```

Returns an array of status definition objects:

```json
[
    {"id": 601, "name": "Passed", "color": "#6cc644", "is_default": false},
    {"id": 602, "name": "Failed", "color": "#bd2c00", "is_default": false},
    {"id": 603, "name": "Blocked", "color": "#f9a825", "is_default": false},
    {"id": 604, "name": "Unexecuted", "color": "#999999", "is_default": true},
    {"id": 605, "name": "Incomplete", "color": "#ff9800", "is_default": false}
]
```

The pipeline builds a lookup map:

```python
status_map = {s["id"]: s["name"] for s in resp.json()}
# Result: {601: "Passed", 602: "Failed", 603: "Blocked", ...}
```

**Code reference**: `get_execution_statuses()` from `smoke_tests/07_test_full_flow.py` lines 88-92

```python
def get_execution_statuses(session, api_base):
    """Get the status ID -> name mapping."""
    resp = session.get(f"{api_base}/test-runs/execution-statuses")
    resp.raise_for_status()
    return {s["id"]: s["name"] for s in resp.json()}
```

---

## Status Resolution: 3-Fallback Strategy

The execution status of a test run can appear in different locations in the API response depending on the qTest version and how the run was executed. The pipeline uses three approaches in priority order.

**Code reference**: `extract_status_from_run()` from `smoke_tests/07_test_full_flow.py` lines 95-133

### Fallback 1: Properties Array

```python
# Check run["properties"] for a field named "Status"
props = run.get("properties", [])
for prop in props:
    field = prop.get("field_name", "") or prop.get("label", "")
    if field.lower() == "status":
        name = prop.get("field_value_name")  # Display name: "Passed", "Failed", etc.
        if name:
            return name
        val = prop.get("field_value")        # Status ID as fallback
        if val:
            return status_map.get(int(val), f"ID:{val}")
```

This is the most reliable source when present. The `field_value_name` contains the human-readable status string directly.

### Fallback 2: Latest Test Log

```python
# Check run["latest_test_log"]["status"]
log = run.get("latest_test_log") or run.get("test_log")
if log and isinstance(log, dict):
    status_obj = log.get("status", {})
    if status_obj:
        return status_obj.get("name", status_map.get(status_obj.get("id"), "Unknown"))
```

Some qTest configurations embed the latest test log (or a summary of it) in the run object. If present, its `status.name` is used.

### Fallback 3: exe_status Field

```python
# Check run["exe_status"] (numeric status ID)
exe_status = run.get("exe_status")
if exe_status:
    return status_map.get(exe_status, f"ID:{exe_status}")
```

The `exe_status` field is a numeric ID that must be resolved using the `status_map` from API Call A.

### If All Fail

Returns `"Unknown"`. This is included in the report counts and noted in `data_collection_issues`.

---

## Identifying Failures

After resolving the status for every test run, the pipeline filters for runs that need detailed investigation:

```python
FAILURE_STATUSES = {"Failed", "Blocked"}

failed_runs = [
    run for run in all_runs
    if extract_status_from_run(run, status_map) in FAILURE_STATUSES
]
```

Both "Failed" and "Blocked" runs get detailed failure logs, because:
- **Failed**: Something went wrong during execution -- the report needs to explain what
- **Blocked**: The test could not execute due to a dependency or environment issue -- equally important to surface

---

## API Call B: Get Failure Logs (per failed/blocked run)

```
GET /api/v3/projects/{projectId}/test-runs/{runId}/test-logs/last-run?expand=teststeplog.teststep
```

This is the **new integration** not present in `07_test_full_flow.py`. It is based on `get_latest_test_log()` from `smoke_tests/06_test_get_logs.py` lines 24-37:

```python
def get_latest_test_log(session, api_base, test_run_id, expand=None):
    """Fetch the latest (most recent) test log for a test run."""
    params = {}
    if expand:
        params["expand"] = expand

    url = f"{api_base}/test-runs/{test_run_id}/test-logs/last-run"
    resp = session.get(url, params=params)
    if resp.status_code == 404:
        return None  # Run has never been executed
    resp.raise_for_status()
    return resp.json()
```

### The `expand=teststeplog.teststep` Parameter

Without this parameter, test step logs are either absent or contain only IDs. With it, each step log includes the full step definition (description, expected result) alongside the actual result. This is critical for explaining failures.

### Calling Pattern in the Pipeline

```python
for run in failed_runs:
    run_id = run["id"]
    run_pid = run.get("pid", f"ID:{run_id}")

    log = get_latest_test_log(session, api_base, run_id, expand="teststeplog.teststep")

    if log is None:
        # Run was never executed (marked Failed manually?)
        data_collection_issues.append(
            f"{run_pid}: No test log found (404) -- run may be unexecuted"
        )
        continue

    failure_detail = extract_failure_detail(run, log)
    failures.append(failure_detail)
```

---

## What We Extract from Each Failure Log

The test log response contains rich execution data. Here is what the pipeline extracts:

### Top-Level Fields

| Field | Type | Purpose |
|-------|------|---------|
| `status.name` | string | Confirms the failure status ("Failed", "Blocked") |
| `exe_start_date` | ISO 8601 string | When the execution started |
| `exe_end_date` | ISO 8601 string | When the execution ended |
| `note` | string or null | Tester's notes or automation error message |

### The `note` Field: Most Valuable Field

The `note` field is the single most valuable piece of data for the morning report. It typically contains:

- **Manual testing**: The tester's description of what went wrong
- **Automated testing**: The exception message, stack trace, or assertion error
- **Example**: `"AssertionError: Expected status 200 but got 500 on /api/users endpoint"`

The pipeline passes this through to the JSON output verbatim (truncated to 500 characters to keep the report manageable).

### Test Step Logs: Finding the Failed Step

The `test_step_logs` array contains one entry per test step in the execution. The pipeline finds the first non-passing step:

```python
def find_failed_step(test_step_logs):
    """Find the first step that did not pass."""
    for step in sorted(test_step_logs, key=lambda s: s.get("order", 0)):
        status = step.get("status", "")
        # status can be a string or a dict depending on qTest version
        if isinstance(status, dict):
            status_name = status.get("name", "")
        else:
            status_name = str(status)

        if status_name.lower() != "passed":
            return {
                "order": step.get("order"),
                "description": step.get("description", ""),
                "expected": step.get("expected_result", ""),
                "actual": step.get("actual_result", ""),
                "status": status_name
            }

    return None  # All steps passed (unusual for a failed run)
```

From the failed step, we extract:

| Field | Source | Example |
|-------|--------|---------|
| `order` | `step.order` | `2` |
| `description` | `step.description` | "Verify error message displayed" |
| `expected` | `step.expected_result` | "Error message shown" |
| `actual` | `step.actual_result` | "Page crashed with 500 error" |

---

## Complete Failure Detail Extraction

```python
def extract_failure_detail(run, log, suite_pid, suite_name):
    """Build a failure detail record from a run and its latest log."""

    # Find the failed step
    step_logs = log.get("test_step_logs", [])
    failed_step = find_failed_step(step_logs) if step_logs else None

    detail = {
        "run_pid": run.get("pid", f"ID:{run['id']}"),
        "run_name": run.get("name", "Unknown"),
        "suite_pid": suite_pid,
        "suite_name": suite_name,
        "status": log.get("status", {}).get("name", "Unknown"),
        "failed_step": failed_step,
        "note": (log.get("note") or "")[:500],  # Truncate long notes
        "executed_at": log.get("exe_start_date"),
    }

    return detail
```

---

## Edge Cases

### 404 on Test Log

A 404 means the test run has never been executed. This can happen when:
- A run was manually marked as "Failed" or "Blocked" without actually executing it
- The run was created but the execution was deleted

**Handling**: Skip the run gracefully. Add a note to `data_collection_issues`:
```
"TR-1005: No test log found (404) -- run may be unexecuted or manually marked"
```

### No test_step_logs in Response

Some qTest configurations do not track step-level results, or the test case has no defined steps.

**Handling**: Report `"failed_step": null` and include the note:
```
"No step details available -- check execution notes"
```

The `note` field becomes the primary source of failure information in this case.

### All Steps Passed but Run is Failed

This edge case occurs when:
- All individual steps passed but the tester manually set the run status to "Failed"
- An automation framework marked the run as failed due to a post-execution check

**Handling**: Report the anomaly explicitly:
```json
{
    "failed_step": null,
    "note": "Run marked as Failed but all steps passed -- check execution notes",
    ...
}
```

### Run Status is "Blocked"

Blocked runs are treated the same as failed runs for log retrieval. However, blocked runs often have:
- No test step logs (the test was never started)
- A `note` explaining the blocking reason (environment down, dependency failed, etc.)

The pipeline does not distinguish between Failed and Blocked in its log-retrieval logic, but the status is preserved in the output so the agent can format them differently in the report.

### Large Number of Failures

If a cycle has 50+ failures, the pipeline fetches logs for all of them. This could mean 50+ API calls. For the expected use case (5-10 failures per cycle), this takes a few seconds. For extreme cases:

- 50 failures: ~50 API calls, ~15-30 seconds
- 100 failures: ~100 API calls, ~30-60 seconds

No parallelism is used (calls are sequential), which provides natural rate limiting. If performance becomes an issue, the pipeline could cap failure log retrieval (e.g., first 20 failures only) and note the truncation.

---

## API Call Summary for Phase 4

| Call | Endpoint | Count | Purpose |
|------|----------|-------|---------|
| A | `GET /test-runs/execution-statuses` | 1 | Build status ID-to-name map |
| B | `GET /test-runs/{id}/test-logs/last-run?expand=teststeplog.teststep` | F (one per failure) | Get detailed failure information |

Where F = number of runs with status "Failed" or "Blocked".
