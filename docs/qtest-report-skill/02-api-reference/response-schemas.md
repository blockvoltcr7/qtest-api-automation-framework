# Response Schemas

Trimmed response schemas documenting only the fields the report skill extracts from each API response. For complete unabridged schemas, see `smoke_tests/DEVELOPER_GUIDE.md` Section 6.

---

## Call 1 — Test Cycle (Resolve Cycle)

**Endpoint**: `GET /test-cycles?expand=descendants`

### Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `number` | Numeric internal ID. Used as `parentId` in Call 2 and Call 3. |
| `pid` | `string` | Human-readable PID (e.g., `CL-416`). This is what the skill searches for. |
| `name` | `string` | Cycle display name. Used in the report header. |
| `test_cycles` | `array` | Recursive list of child cycles. The skill searches these depth-first. |
| `test_suites` | `array` | Child test suites embedded when `expand=descendants` is used. |

### Trimmed Response Example

```json
[
  {
    "id": 10200,
    "pid": "CL-400",
    "name": "Release 5.0",
    "test_cycles": [
      {
        "id": 67890,
        "pid": "CL-416",
        "name": "Sprint 42 - Regression",
        "test_cycles": [],
        "test_suites": [
          {
            "id": 54321,
            "pid": "TC-970",
            "name": "Smoke Tests"
          },
          {
            "id": 54322,
            "pid": "TC-971",
            "name": "Integration Tests"
          }
        ]
      }
    ],
    "test_suites": []
  }
]
```

### Notes

- The top-level response is an **array** of root cycles.
- The `test_cycles` field is recursive: each child cycle can contain its own `test_cycles` and `test_suites`.
- The skill walks the entire tree until it finds a cycle whose `pid` matches the target. The search is depth-first, left-to-right.
- The `expand=descendants` parameter is what causes `test_suites` to be populated within each cycle node. Without it, only the top-level cycles are returned.

---

## Call 2 — Test Suite (Get Suites)

**Endpoint**: `GET /test-suites?parentId={cycleId}&parentType=test-cycle`

### Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `number` | Numeric suite ID. Used as `parentId` in Call 3. |
| `pid` | `string` | Human-readable PID (e.g., `TC-970`). Included in the report for traceability. |
| `name` | `string` | Suite display name. Used as a section heading in the report. |

### Trimmed Response Example

```json
[
  {
    "id": 54321,
    "pid": "TC-970",
    "name": "Smoke Tests"
  },
  {
    "id": 54322,
    "pid": "TC-971",
    "name": "Integration Tests"
  },
  {
    "id": 54323,
    "pid": "TC-972",
    "name": "E2E Checkout Flow"
  }
]
```

### Notes

- Response is a flat array. No nesting.
- If the cycle contains no suites, the response is an empty array `[]`. The pipeline still proceeds to Call 3 to fetch runs directly under the cycle.

---

## Call 3 — Test Run (Get Runs)

**Endpoint**: `GET /test-runs?parentId={id}&parentType={type}&page={n}&pageSize=100`

### Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `number` | Numeric run ID. Used in Call 5 URL for failed/blocked runs. |
| `pid` | `string` | Human-readable PID (e.g., `TR-1001`). Included in the report. |
| `name` | `string` | Test run display name (typically mirrors the linked test case name). |
| `properties` | `array` | Array of field objects. The skill looks for the entry with `field_name == "Status"`. |
| `properties[].field_name` | `string` | Field identifier. The skill filters for `"Status"`. |
| `properties[].field_value` | `string` | Numeric status ID as a string (e.g., `"601"`). Used for lookup against Call 4 results. |
| `properties[].field_value_name` | `string` | Human-readable status name (e.g., `"Passed"`). Preferred source for status. |

### Trimmed Response Example

```json
[
  {
    "id": 98765,
    "pid": "TR-1001",
    "name": "Verify login with valid credentials",
    "properties": [
      {
        "field_name": "Status",
        "field_value": "601",
        "field_value_name": "Passed"
      }
    ]
  },
  {
    "id": 98766,
    "pid": "TR-1002",
    "name": "Verify login with expired token",
    "properties": [
      {
        "field_name": "Status",
        "field_value": "602",
        "field_value_name": "Failed"
      }
    ]
  },
  {
    "id": 98767,
    "pid": "TR-1003",
    "name": "Verify MFA prompt on new device",
    "properties": [
      {
        "field_name": "Status",
        "field_value": "603",
        "field_value_name": "Blocked"
      }
    ]
  }
]
```

### Status Field Variations

The status of a test run can appear in **three different locations** depending on qTest version, project configuration, and whether the run has been executed. The skill checks all three in fallback order:

| Priority | Path | Description |
|----------|------|-------------|
| 1 (preferred) | `properties[field_name="Status"].field_value_name` | Most reliable. Present in the `properties` array. |
| 2 (fallback) | `latest_test_log.status.name` | Available when the run has at least one execution log. |
| 3 (last resort) | `exe_status` | Legacy field. Sometimes a numeric ID, sometimes a name string. Cross-reference with Call 4 status map if numeric. |

The skill iterates through these in order and uses the first non-null value. If all three are absent, the run status is recorded as `"Unknown"`.

---

## Call 4 — Execution Status (Get Statuses)

**Endpoint**: `GET /test-runs/execution-statuses`

### Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `number` | Numeric status ID. Used as the key in the status lookup map. |
| `name` | `string` | Human-readable status name (e.g., `"Passed"`, `"Failed"`, `"Blocked"`, `"Unexecuted"`). |

### Trimmed Response Example

```json
[
  {
    "id": 601,
    "name": "Passed"
  },
  {
    "id": 602,
    "name": "Failed"
  },
  {
    "id": 603,
    "name": "Blocked"
  },
  {
    "id": 604,
    "name": "Unexecuted"
  },
  {
    "id": 605,
    "name": "Incomplete"
  }
]
```

### Notes

- Status IDs are **project-specific**. Do not hardcode them. ID `601` might mean `"Passed"` in one project and something else in another.
- The skill builds a `dict[int, str]` from this response: `{601: "Passed", 602: "Failed", ...}`.
- This map is used to resolve numeric status references found in Call 3 results (specifically the `field_value` and `exe_status` fields).

---

## Call 5 — Test Log (Get Failure Logs)

**Endpoint**: `GET /test-runs/{runId}/test-logs/last-run?expand=teststeplog.teststep`

### Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | `object` | Contains the execution outcome. |
| `status.name` | `string` | Status name (e.g., `"Failed"`). |
| `exe_start_date` | `string (ISO 8601)` | Execution start timestamp. Used to calculate duration. |
| `exe_end_date` | `string (ISO 8601)` | Execution end timestamp. Used to calculate duration. |
| `note` | `string` | Free-text execution note. Often contains the failure reason or error message. Can be HTML. |
| `test_step_logs` | `array` | Ordered list of step-level results. |
| `test_step_logs[].order` | `number` | 0-indexed step position. |
| `test_step_logs[].status` | `string` | Step-level status (e.g., `"Passed"`, `"Failed"`). |
| `test_step_logs[].description` | `string` | What the step does (action). |
| `test_step_logs[].expected_result` | `string` | What should happen. |
| `test_step_logs[].actual_result` | `string` | What actually happened. Key field for failure diagnosis. |

### Trimmed Response Example

```json
{
  "status": {
    "name": "Failed"
  },
  "exe_start_date": "2026-03-22T14:30:00Z",
  "exe_end_date": "2026-03-22T14:35:00Z",
  "note": "Server returned 500 on login submission",
  "test_step_logs": [
    {
      "order": 0,
      "status": "Passed",
      "description": "Navigate to login page",
      "expected_result": "Page loads successfully with login form",
      "actual_result": "Page loaded in 1.2s"
    },
    {
      "order": 1,
      "status": "Passed",
      "description": "Enter valid username and password",
      "expected_result": "Fields accept input",
      "actual_result": "Credentials entered"
    },
    {
      "order": 2,
      "status": "Failed",
      "description": "Submit login form",
      "expected_result": "Redirect to dashboard within 3 seconds",
      "actual_result": "500 Internal Server Error — response body: {\"error\": \"database connection timeout\"}"
    }
  ]
}
```

### Notes

- The `note` field can contain **HTML markup**. The skill strips HTML tags before including the note in the report.
- The `test_step_logs` array is ordered by the `order` field (0-indexed). Steps are rendered in this order in the failure analysis section.
- If `exe_start_date` or `exe_end_date` is `null`, the duration is reported as `"N/A"`.
- The `expand=teststeplog.teststep` parameter is required to populate `test_step_logs`. Without it, the array is either absent or empty.
- A `404` response on this endpoint means the run has never been executed. This is expected for unexecuted runs that happen to appear in the failed filter due to status data inconsistencies. The skill skips these gracefully.

---

## Cross-Reference

For complete unabridged schemas including all fields returned by the qTest API (not just those extracted by the skill), see `smoke_tests/DEVELOPER_GUIDE.md` Section 6.
