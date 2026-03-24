# Phase 5: Analyze & Output JSON

## Purpose

Aggregate all data collected in Phases 1-4 into a structured JSON blob and write it to stdout. This JSON is the contract between the pipeline script and the Claude Code agent. The agent reads it and formats the markdown morning report.

Phase 5 makes zero API calls. It is pure computation.

---

## Aggregation Using `collections.Counter`

### Overall Statistics

```python
from collections import Counter

overall_stats = Counter()
for run in all_runs:
    status_name = extract_status_from_run(run, status_map)
    overall_stats[status_name] += 1
```

The `Counter` produces a dictionary like:
```python
{"Passed": 45, "Failed": 5, "Blocked": 2, "Incomplete": 1, "Unexecuted": 8}
```

### Per-Suite Statistics

```python
suite_results = []
for suite in suites:
    suite_pid = suite.get("pid")
    runs = suite_runs.get(suite_pid, [])

    suite_stats = Counter()
    for run in runs:
        suite_stats[extract_status_from_run(run, status_map)] += 1

    total = sum(suite_stats.values())
    passed = suite_stats.get("Passed", 0)
    executed = total - suite_stats.get("Unexecuted", 0)

    suite_results.append({
        "pid": suite_pid,
        "name": suite.get("name"),
        "id": suite.get("id"),
        "total": total,
        "passed": passed,
        "failed": suite_stats.get("Failed", 0),
        "blocked": suite_stats.get("Blocked", 0),
        "incomplete": suite_stats.get("Incomplete", 0),
        "unexecuted": suite_stats.get("Unexecuted", 0),
        "pass_rate": round(passed / executed * 100, 1) if executed > 0 else None,
    })
```

### Pass Rate Calculation

```
pass_rate = passed / (total - unexecuted) * 100
```

**Why exclude unexecuted?** Unexecuted runs have not been attempted yet. Including them in the denominator would artificially deflate the pass rate. The pass rate answers: "Of the tests we actually ran, what percentage passed?"

| Scenario | Passed | Failed | Unexecuted | Total | Pass Rate |
|----------|--------|--------|------------|-------|-----------|
| All passing | 50 | 0 | 0 | 50 | 100.0% |
| Some failures | 45 | 5 | 0 | 50 | 90.0% |
| With unexecuted | 45 | 5 | 10 | 60 | 90.0% (not 75%) |
| None executed | 0 | 0 | 50 | 50 | null |

When `executed == 0`, the pass rate is `null` (not 0, not undefined), because division by zero is mathematically undefined and reporting 0% would be misleading.

---

## Failure Detail Records

For each failed or blocked run (enriched in Phase 4), the pipeline produces a structured record:

```json
{
    "run_pid": "TR-1002",
    "run_name": "Verify login with invalid password",
    "suite_pid": "TS-970",
    "suite_name": "Smoke Tests",
    "status": "Failed",
    "failed_step": {
        "order": 2,
        "description": "Verify error message displayed",
        "expected": "Error message shown",
        "actual": "Page crashed with 500 error"
    },
    "note": "Server returned 500 instead of validation error",
    "executed_at": "2026-03-22T14:30:00Z"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `run_pid` | string | Test run PID (e.g., "TR-1002") |
| `run_name` | string | Human-readable test name |
| `suite_pid` | string | Parent suite PID, or "(direct)" if not in a suite |
| `suite_name` | string | Parent suite name |
| `status` | string | "Failed" or "Blocked" |
| `failed_step` | object or null | First non-passing step with order, description, expected, actual |
| `note` | string | Execution note (truncated to 500 chars) -- error messages, tester notes |
| `executed_at` | string or null | ISO 8601 timestamp of execution start |

### When `failed_step` is null

This happens when:
- The test has no defined steps
- All steps passed but the run was marked Failed manually
- The test log had no step-level data

In these cases, the `note` field is the primary source of failure information.

---

## Complete JSON Output Schema

This is the contract between the pipeline and the agent. The pipeline writes this to stdout; the agent parses it.

```json
{
    "cycle_pid": "CL-416",
    "cycle_name": "Sprint 42 Regression Cycle",
    "cycle_id": 67890,
    "generated_at": "2026-03-23T09:00:00Z",
    "summary": {
        "total_runs": 61,
        "executed": 53,
        "passed": 45,
        "failed": 5,
        "blocked": 2,
        "incomplete": 1,
        "unexecuted": 8,
        "pass_rate": 84.9,
        "other_statuses": {}
    },
    "suites": [
        {
            "pid": "TS-970",
            "name": "Smoke Tests",
            "id": 54321,
            "total": 30,
            "passed": 25,
            "failed": 3,
            "blocked": 2,
            "incomplete": 0,
            "unexecuted": 0,
            "pass_rate": 83.3
        },
        {
            "pid": "TS-971",
            "name": "Regression Tests",
            "id": 54322,
            "total": 25,
            "passed": 20,
            "failed": 2,
            "blocked": 0,
            "incomplete": 1,
            "unexecuted": 2,
            "pass_rate": 87.0
        }
    ],
    "failures": [
        {
            "run_pid": "TR-1002",
            "run_name": "Verify login with invalid password",
            "suite_pid": "TS-970",
            "suite_name": "Smoke Tests",
            "status": "Failed",
            "failed_step": {
                "order": 2,
                "description": "Verify error message displayed",
                "expected": "Error message shown",
                "actual": "Page crashed with 500 error"
            },
            "note": "Server returned 500 instead of validation error",
            "executed_at": "2026-03-22T14:30:00Z"
        }
    ],
    "blocked_items": [
        {
            "run_pid": "TR-1010",
            "run_name": "Verify payment processing",
            "suite_pid": "TS-970",
            "suite_name": "Smoke Tests",
            "status": "Blocked",
            "failed_step": null,
            "note": "Payment gateway sandbox is down since 2026-03-21",
            "executed_at": "2026-03-22T10:00:00Z"
        }
    ],
    "data_collection_issues": []
}
```

### Top-Level Fields

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `cycle_pid` | string | Yes | Input cycle PID echoed back |
| `cycle_name` | string | Yes | Human-readable cycle name from qTest |
| `cycle_id` | int | Yes | Numeric cycle ID |
| `generated_at` | string | Yes | ISO 8601 timestamp when the pipeline ran |
| `summary` | object | Yes | Overall aggregated statistics |
| `suites` | array | Yes | Per-suite breakdown (may be empty) |
| `failures` | array | Yes | Detailed records for Failed runs (may be empty) |
| `blocked_items` | array | Yes | Detailed records for Blocked runs (may be empty) |
| `data_collection_issues` | array | Yes | Warnings and non-fatal errors (may be empty) |

### The `summary` Object

| Field | Type | Description |
|-------|------|-------------|
| `total_runs` | int | Total test runs across all suites |
| `executed` | int | `total_runs - unexecuted` |
| `passed` | int | Runs with status "Passed" |
| `failed` | int | Runs with status "Failed" |
| `blocked` | int | Runs with status "Blocked" |
| `incomplete` | int | Runs with status "Incomplete" |
| `unexecuted` | int | Runs with status "Unexecuted" |
| `pass_rate` | float or null | `passed / executed * 100`, null if executed == 0 |
| `other_statuses` | object | Any statuses not in the standard set, e.g., `{"In Progress": 3}` |

The `other_statuses` field captures custom statuses that some qTest instances define. These are counted separately so the standard fields always have predictable meanings.

### The `suites` Array

Each entry mirrors the `summary` structure but scoped to a single suite. The `pid`, `name`, and `id` fields identify the suite.

### The `failures` and `blocked_items` Arrays

These are separated into two arrays so the agent can format them differently in the report:
- **Failures** get a "What broke?" section with step-level details
- **Blocked items** get a "What's blocked?" section focused on the blocking reason in the `note` field

### The `data_collection_issues` Array

Non-fatal warnings encountered during data collection. Examples:

```json
[
    "TR-1005: No test log found (404) -- run may be unexecuted or manually marked",
    "TR-1012: Status could not be resolved (returned 'Unknown')",
    "TS-980: Suite returned 0 runs -- may be empty or permissions issue"
]
```

The agent can include these at the bottom of the report as a "Data Notes" section, or omit them if the array is empty.

---

## Assembling the Output

```python
import json
import sys
from datetime import datetime, timezone

output = {
    "cycle_pid": cycle_pid,
    "cycle_name": cycle_name,
    "cycle_id": cycle_id,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "total_runs": total,
        "executed": total - overall_stats.get("Unexecuted", 0),
        "passed": overall_stats.get("Passed", 0),
        "failed": overall_stats.get("Failed", 0),
        "blocked": overall_stats.get("Blocked", 0),
        "incomplete": overall_stats.get("Incomplete", 0),
        "unexecuted": overall_stats.get("Unexecuted", 0),
        "pass_rate": pass_rate,
        "other_statuses": {
            k: v for k, v in overall_stats.items()
            if k not in {"Passed", "Failed", "Blocked", "Incomplete", "Unexecuted"}
        },
    },
    "suites": suite_results,
    "failures": [f for f in failure_details if f["status"] == "Failed"],
    "blocked_items": [f for f in failure_details if f["status"] == "Blocked"],
    "data_collection_issues": data_collection_issues,
}

# Write JSON to stdout -- this is what the agent reads
json.dump(output, sys.stdout, indent=2)
```

---

## Exit Codes

| Exit Code | Meaning | Stdout | Stderr |
|-----------|---------|--------|--------|
| 0 | Success | JSON output | (empty or debug messages) |
| 1 | Fatal error | (empty) | Error message describing the failure |

### How the Agent Uses Exit Codes

```
IF exit_code == 0:
    Parse JSON from stdout
    Format markdown report
ELSE:
    Read error message from stderr
    Report the error to the user
```

---

## Relationship to Report Formatting

The pipeline deliberately does NOT format markdown. The JSON output is the interface contract. The agent formats the report using the template defined in `05-report-design/`.

This separation provides:

1. **Testability**: The pipeline can be tested by asserting on JSON structure, not markdown strings.
2. **Flexibility**: The agent can adapt the report format (add context, change wording, highlight trends) without changing Python code.
3. **Reusability**: The same JSON output could be consumed by other tools (dashboards, Slack bots, etc.) in the future.

---

## Example: Minimal Output (Empty Cycle)

```json
{
    "cycle_pid": "CL-999",
    "cycle_name": "Empty Cycle",
    "cycle_id": 99999,
    "generated_at": "2026-03-23T09:00:00Z",
    "summary": {
        "total_runs": 0,
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "incomplete": 0,
        "unexecuted": 0,
        "pass_rate": null,
        "other_statuses": {}
    },
    "suites": [],
    "failures": [],
    "blocked_items": [],
    "data_collection_issues": [
        "No test suites found under CL-999"
    ]
}
```

The agent would render this as a short report noting that the cycle has no test data yet.

## Example: Perfect Run (No Failures)

```json
{
    "cycle_pid": "CL-500",
    "cycle_name": "Nightly Smoke",
    "cycle_id": 50000,
    "generated_at": "2026-03-23T09:00:00Z",
    "summary": {
        "total_runs": 40,
        "executed": 40,
        "passed": 40,
        "failed": 0,
        "blocked": 0,
        "incomplete": 0,
        "unexecuted": 0,
        "pass_rate": 100.0,
        "other_statuses": {}
    },
    "suites": [
        {
            "pid": "TS-100",
            "name": "Core Smoke",
            "id": 10000,
            "total": 40,
            "passed": 40,
            "failed": 0,
            "blocked": 0,
            "incomplete": 0,
            "unexecuted": 0,
            "pass_rate": 100.0
        }
    ],
    "failures": [],
    "blocked_items": [],
    "data_collection_issues": []
}
```

The agent would render this as a green-light report: all 40 tests passed, no action items.
