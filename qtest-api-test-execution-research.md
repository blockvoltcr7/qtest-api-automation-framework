# qTest API Research: Test Execution — Test Cycles, Test Suites & Statistics

**Date:** 2026-03-23
**Scope:** Retrieve a Test Cycle (e.g. CL-416), list its child Test Suites (TC-970, TC-498, …), and gather execution statistics.

---

## 1. Authentication

All API calls require a Bearer token obtained via the Login endpoint.

```
POST /oauth/token
```

**Headers:**
```
Authorization: Basic base64(client_id:client_secret)
Content-Type: application/x-www-form-urlencoded
```

**Body:**
```
grant_type=password&username={email}&password={password}
```

**Response:** Returns an `access_token` to use as `Bearer {token}` in all subsequent calls.

> **Note:** You can also use a permanent API token generated from the **Download qTest Resources** page in Site Administration. This token never expires unless revoked.

---

## 2. Base URL Pattern

```
https://{your-domain}.qtestnet.com/api/v3/projects/{projectId}/...
```

You need your **qTest domain** and the numeric **Project ID**.

---

## 3. Scenario Walkthrough: CL-416 → Test Suites → Statistics

### Step 1: Resolve the Test Cycle PID ("CL-416") to its numeric ID

The qTest API endpoints use **numeric IDs** internally, but responses include a `pid` field (e.g. `"CL-416"`). There are two approaches to resolve a PID:

**Option A — Get all cycles and filter by PID:**

```
GET /api/v3/projects/{projectId}/test-cycles?expand=descendants
```

This returns all test cycles with their `pid` field. Search the response for the object where `pid == "CL-416"` and extract its `id`.

**Option B — If you already know the numeric ID:**

```
GET /api/v3/projects/{projectId}/test-cycles/{testCycleId}
```

**Response fields of interest:**
| Field | Description |
|-------|-------------|
| `id` | Numeric internal ID (e.g. `119927`) |
| `pid` | Human-readable project ID (e.g. `"CL-416"`) |
| `name` | Test cycle name |
| `description` | Description text |
| `web_url` | Direct link to the cycle in the qTest UI |
| `links` | HATEOAS links to child resources (test-suites, test-runs) |

**Key parameter:** `expand=descendants` — retrieves the full tree of child test cycles and test suites in a single call.

---

### Step 2: Get Test Suites inside the Test Cycle

Once you have the numeric ID of CL-416 (let's say it's `{cycleId}`):

```
GET /api/v3/projects/{projectId}/test-suites?parentId={cycleId}&parentType=test-cycle
```

**Response:** Array of `TestSuiteWithCustomFieldResource` objects:

```json
[
  {
    "id": 54321,
    "pid": "TC-970",
    "name": "Smoke Tests",
    "web_url": "https://...",
    "links": [
      { "rel": "test-runs", "href": "..." }
    ]
  },
  {
    "id": 54322,
    "pid": "TC-498",
    "name": "Regression Suite",
    "web_url": "https://...",
    "links": [...]
  }
]
```

**Alternative (single call):** Use `expand=descendants` on the test cycle GET to retrieve both nested cycles AND suites in one request:

```
GET /api/v3/projects/{projectId}/test-cycles/{cycleId}?expand=descendants
```

---

### Step 3: Get Test Runs inside each Test Suite

For each test suite, retrieve its test runs:

```
GET /api/v3/projects/{projectId}/test-runs?parentId={testSuiteId}&parentType=test-suite
```

You can also get test runs directly under the test cycle:

```
GET /api/v3/projects/{projectId}/test-runs?parentId={cycleId}&parentType=test-cycle
```

**Response fields per test run:**
| Field | Description |
|-------|-------------|
| `id` | Test run numeric ID |
| `pid` | Test run PID |
| `name` | Test run name |
| `properties` | Array of field values (includes Status) |
| `links` | Links to test-logs, test-case |
| `test_case` | Linked test case info (with `expand=testcase`) |

---

### Step 4: Get Execution Statuses (for statistics mapping)

```
GET /api/v3/projects/{projectId}/test-runs/execution-statuses
```

**Response:** Returns all configured execution statuses:

```json
[
  { "id": 601, "name": "Passed", "color": "#6cc644", "is_default": false },
  { "id": 602, "name": "Failed", "color": "#d0021b", "is_default": false },
  { "id": 603, "name": "Incomplete", "color": "#f5a623", "is_default": false },
  { "id": 604, "name": "Blocked", "color": "#8b572a", "is_default": false },
  { "id": 605, "name": "Unexecuted", "color": "#999999", "is_default": true }
]
```

---

### Step 5: Get Latest Test Log for each Test Run

```
GET /api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs/last-run
```

Optional: `expand=teststeplog.teststep` to include step-level results.

**Response includes:** `status` object (with id, name), `exe_start_date`, `exe_end_date`, `note`, `attachments`, `test_step_logs`.

---

### Step 6: Compute Statistics (client-side aggregation)

qTest does **not** have a dedicated "statistics" endpoint for test cycles. You need to:

1. Retrieve all test runs under the cycle (or under each suite)
2. Map each test run's latest status to the execution status names
3. Aggregate counts by status

**Pseudocode:**
```python
stats = {"Passed": 0, "Failed": 0, "Incomplete": 0, "Blocked": 0, "Unexecuted": 0}

for test_run in all_test_runs:
    status_name = test_run["properties"]["Status"]  # or from latest test-log
    stats[status_name] += 1
```

---

## 4. Complete API Endpoint Reference

### Test Cycle APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v3/projects/{projectId}/test-cycles/{testCycleId}` | Get a single test cycle |
| `GET` | `/api/v3/projects/{projectId}/test-cycles` | Get all test cycles (supports `parentId`, `parentType`, `expand`) |
| `POST` | `/api/v3/projects/{projectId}/test-cycles` | Create a test cycle |
| `PUT` | `/api/v3/projects/{projectId}/test-cycles/{testCycleId}` | Update/move a test cycle |
| `DELETE` | `/api/v3/projects/{projectId}/test-cycles/{testCycleId}` | Delete a test cycle (`force=true` for with children) |

### Test Suite APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v3/projects/{projectId}/test-suites/{testSuiteId}` | Get a single test suite |
| `GET` | `/api/v3/projects/{projectId}/test-suites?parentId={id}&parentType=test-cycle` | Get suites under a test cycle |
| `GET` | `/api/v3/projects/{projectId}/settings/test-suites/fields` | Get test suite field definitions |
| `POST` | `/api/v3/projects/{projectId}/test-suites` | Create a test suite |
| `PUT` | `/api/v3/projects/{projectId}/test-suites/{testSuiteId}` | Update/move a test suite |
| `DELETE` | `/api/v3/projects/{projectId}/test-suites/{testSuiteId}` | Delete a test suite |

### Test Run APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v3/projects/{projectId}/test-runs/{testRunId}` | Get a single test run (`expand=testcase.teststep`) |
| `GET` | `/api/v3/projects/{projectId}/test-runs?parentId={id}&parentType=test-suite` | Get runs under a test suite |
| `GET` | `/api/v3/projects/{projectId}/test-runs?parentId={id}&parentType=test-cycle` | Get runs under a test cycle |
| `GET` | `/api/v3/projects/{projectId}/test-runs/execution-statuses` | Get all execution status definitions |
| `POST` | `/api/v3/projects/{projectId}/test-runs` | Create a test run |
| `PUT` | `/api/v3/projects/{projectId}/test-runs/{testRunId}` | Update/move a test run |
| `DELETE` | `/api/v3/projects/{projectId}/test-runs/{testRunId}` | Delete a test run |

### Test Log APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs/last-run` | Get latest execution result |
| `GET` | `/api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs` | Get all test logs (paginated) |
| `POST` | `/api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs` | Submit a manual test log |
| `POST` | `/api/v3/projects/{projectId}/test-runs/{testRunId}/auto-test-logs` | Submit an automation test log |

### Search API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v3/projects/{projectId}/search` | Query test-runs, test-cases, requirements, defects |

**Search body example (find test runs):**
```json
{
  "object_type": "test-runs",
  "fields": ["*"],
  "query": "'Status' = 'Failed'"
}
```

---

## 5. Recommended API Call Flow for Agent Skill

```
┌─────────────────────────────────────────────────┐
│  1. Authenticate                                │
│     POST /oauth/token → Bearer token            │
├─────────────────────────────────────────────────┤
│  2. Get Test Cycle (with descendants)           │
│     GET .../test-cycles?expand=descendants      │
│     → Find CL-416 by pid, get numeric id        │
├─────────────────────────────────────────────────┤
│  3. Get Test Suites under the cycle             │
│     GET .../test-suites?parentId=X              │
│        &parentType=test-cycle                   │
│     → Returns TC-970, TC-498, etc.              │
├─────────────────────────────────────────────────┤
│  4. For each Test Suite, get Test Runs          │
│     GET .../test-runs?parentId=Y                │
│        &parentType=test-suite                   │
├─────────────────────────────────────────────────┤
│  5. Get execution statuses reference            │
│     GET .../test-runs/execution-statuses        │
├─────────────────────────────────────────────────┤
│  6. Aggregate: count runs per status            │
│     → { Passed: 45, Failed: 3, ... }           │
└─────────────────────────────────────────────────┘
```

---

## 6. Rate Limiting & Pagination Notes

- **Rate limit:** API calls that occur too frequently return `429 Too Many Requests`
- **Pagination:** List endpoints support `page` (default 1) and `pageSize` (default 100, max 999-1000)
- **Plan tier:** V3 APIs require **Premium** or **Elite** qTest packages

---

## 7. Key Identifiers Cheat Sheet

| Prefix | Object Type | Example |
|--------|-------------|---------|
| `CL-`  | Test Cycle  | CL-416  |
| `TC-`  | Test Suite  | TC-970  |
| `TR-`  | Test Run    | TR-1234 |
| `TS-`  | Test Case   | TS-5678 |
| `RQ-`  | Requirement | RQ-100  |

---

## Sources

- [qTest Test Cycle APIs (Tricentis)](https://docs.tricentis.com/qtest-saas/content/apis/apis/test_cycle_apis.htm)
- [qTest Test Suite APIs (Tricentis)](https://docs.tricentis.com/qtest-saas/content/apis/apis/test_suite_apis.htm)
- [qTest Test Run APIs (Tricentis)](https://docs.tricentis.com/qtest-saas/content/apis/apis/test_run_apis.htm)
- [qTest API Specification Overview](https://documentation.tricentis.com/qtest/od/en/content/apis/overview/qtest_api_specification.htm)
- [qTest Swagger Client - TestCycleApi](https://github.com/rcbops/qtest-swagger-client/blob/master/docs/TestcycleApi.md)
- [qTest Swagger Client - TestSuiteApi](https://github.com/rcbops/qtest-swagger-client/blob/master/docs/TestsuiteApi.md)
- [qTest Swagger Client - TestRunApi](https://github.com/rcbops/qtest-swagger-client/blob/master/docs/TestrunApi.md)
- [qTest Swagger Client - SearchApi](https://github.com/rcbops/qtest-swagger-client/blob/master/docs/SearchApi.md)
- [qTest Common APIs](https://docs.tricentis.com/qtest-11.3/content/apis/apis/common_apis.htm)
