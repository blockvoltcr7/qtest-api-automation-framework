# Input/Output Contract

This document defines the formal contract between every layer of the `/qtest-report` skill.

---

## Contract Overview

```
┌─────────┐    /qtest-report CL-416    ┌───────────┐
│  User    │ ─────────────────────────► │  Agent    │
│          │ ◄───────────────────────── │           │
└─────────┘    Markdown morning report  └─────┬─────┘
                                              │
                                    python pipeline/   │ JSON on stdout
                                    qtest_report_      │ or error on stderr
                                    pipeline.py CL-416 │
                                              │
                                        ┌─────▼──────┐
                                        │  Pipeline   │
                                        │  (Python)   │
                                        └─────┬──────┘
                                              │
                                    5 sequential  │  JSON responses
                                    GET requests   │  or HTTP errors
                                              │
                                        ┌─────▼──────┐
                                        │  qTest API │
                                        │  (v3)      │
                                        └────────────┘
```

---

## Layer 1: User → Agent

### Input

| Field | Type | Required | Example |
|-------|------|----------|---------|
| Command | string | Yes | `/qtest-report` |
| Cycle PID | string | No (agent asks if missing) | `CL-416` |

**Invocation patterns:**
- `/qtest-report CL-416` — full invocation
- `/qtest-report` — agent prompts for the PID

### Output (Success)

Formatted markdown morning report displayed in the terminal. Contains:
- Executive summary with pass rate
- Status breakdown table
- Per-suite results table
- Failure analysis with step-level details
- Blocked items with notes
- Agent-generated recommendations

### Output (Error)

Clear error message with:
- What went wrong (e.g., "401 Unauthorized")
- Why it happened (e.g., "Bearer token is expired")
- How to fix it (e.g., "Regenerate token from qTest Site Admin")

---

## Layer 2: Agent → Python Pipeline

### Input

```bash
python pipeline/qtest_report_pipeline.py CL-416
```

| Argument | Position | Type | Required | Description |
|----------|----------|------|----------|-------------|
| cycle_pid | 1 | string | Yes | Test cycle PID (e.g., "CL-416") |

The agent invokes this via the Bash tool from the repo root directory.

### Output (Success)

- **stdout**: JSON blob matching the schema below
- **stderr**: Progress messages (e.g., `[2/5] Fetching test suites...`)
- **Exit code**: `0`

### Output (Error)

- **stdout**: Empty or partial
- **stderr**: Error message describing the failure
- **Exit code**: `1`

### JSON Output Schema

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
      "pid": "TC-970",
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
      "pid": "TC-498",
      "name": "Regression Suite",
      "id": 54322,
      "total": 23,
      "passed": 20,
      "failed": 2,
      "blocked": 0,
      "incomplete": 1,
      "unexecuted": 0,
      "pass_rate": 87.0
    }
  ],

  "failures": [
    {
      "run_pid": "TR-1002",
      "run_id": 98766,
      "run_name": "Verify login with expired token",
      "suite_pid": "TC-970",
      "suite_name": "Smoke Tests",
      "status": "Failed",
      "failed_step": {
        "order": 3,
        "description": "Verify redirect to login page",
        "expected": "HTTP 302 redirect to /login",
        "actual": "HTTP 500 Internal Server Error"
      },
      "note": "Server returned 500 instead of redirect on expired token",
      "executed_at": "2026-03-22T18:45:00Z"
    }
  ],

  "blocked_items": [
    {
      "run_pid": "TR-1040",
      "run_id": 98790,
      "run_name": "Payment gateway integration",
      "suite_pid": "TC-498",
      "suite_name": "Regression Suite",
      "note": "Staging payment API is down — blocked pending infra fix (JIRA-4521)",
      "executed_at": "2026-03-20T10:00:00Z"
    }
  ],

  "data_collection_issues": []
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `cycle_pid` | string | The PID that was queried |
| `cycle_name` | string | Human-readable cycle name from qTest |
| `cycle_id` | number | Numeric internal ID |
| `generated_at` | string | ISO 8601 timestamp when the report was generated |
| `summary.total_runs` | number | Total test runs across all suites |
| `summary.executed` | number | `total_runs - unexecuted` |
| `summary.passed` | number | Runs with status "Passed" |
| `summary.failed` | number | Runs with status "Failed" |
| `summary.blocked` | number | Runs with status "Blocked" |
| `summary.incomplete` | number | Runs with status "Incomplete" |
| `summary.unexecuted` | number | Runs with status "Unexecuted" |
| `summary.pass_rate` | number | `(passed / executed) * 100`, 0-100 |
| `summary.other_statuses` | object | `{status_name: count}` for any custom statuses |
| `suites[].pid` | string | Suite PID |
| `suites[].name` | string | Suite name |
| `suites[].id` | number | Suite numeric ID |
| `suites[].total` | number | Total runs in this suite |
| `suites[].pass_rate` | number | Suite-level pass rate |
| `failures[].run_pid` | string | Failed run PID |
| `failures[].run_name` | string | Failed run name |
| `failures[].suite_pid` | string | Which suite this run belongs to |
| `failures[].failed_step` | object/null | Step that failed (null if no step details) |
| `failures[].note` | string | Execution note or error message |
| `failures[].executed_at` | string | When the run was last executed |
| `blocked_items[]` | array | Same structure as failures, minus failed_step |
| `data_collection_issues[]` | array of strings | Any API errors encountered during collection |

---

## Layer 3: Python Pipeline → qTest API

### Requests

All requests use:
- **Base URL**: `https://{QTEST_DOMAIN}.qtestnet.com/api/v3/projects/{QTEST_PROJECT_ID}`
- **Headers**: `Authorization: Bearer {token}`, `Content-Type: application/json`, `Accept: application/json`
- **Method**: GET (all 5 calls)
- **Timeout**: 30 seconds per call

### Responses

| Call | Expected | Error Cases |
|------|----------|-------------|
| GET /test-cycles | 200 + JSON array | 401, 429 |
| GET /test-suites | 200 + JSON array | 401, 404, 429 |
| GET /test-runs | 200 + JSON array | 401, 404, 429 |
| GET /execution-statuses | 200 + JSON array | 401, 429 |
| GET /test-logs/last-run | 200 + JSON object | 401, 404 (normal), 429 |

---

## Future Extension Flags (v2+)

These are NOT implemented in v1 but document the design space for future args:

| Flag | Purpose | Example |
|------|---------|---------|
| `--suite` | Filter report to a single suite | `--suite TC-970` |
| `--since` | Filter by execution date | `--since 2026-03-22` |
| `--format` | Alternative output format | `--format html` |
| `--json` | Output raw JSON (skip agent formatting) | `--json` |
| `--compare` | Compare with another cycle | `--compare CL-415` |
| `--top-failures` | Limit failure details shown | `--top-failures 10` |
