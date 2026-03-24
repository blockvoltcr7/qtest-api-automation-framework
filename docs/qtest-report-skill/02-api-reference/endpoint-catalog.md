# Endpoint Catalog

Complete reference for the 5 qTest API calls the report skill executes, listed in pipeline order.

## Base URL

```
https://{domain}.qtestnet.com/api/v3/projects/{projectId}
```

Where:
- `{domain}` is sourced from the `QTEST_DOMAIN` environment variable (e.g., `acme` resolves to `acme.qtestnet.com`)
- `{projectId}` is sourced from the `QTEST_PROJECT_ID` environment variable (numeric project ID)

## Common Headers

All calls require the same header set:

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer {token}` where `{token}` is `QTEST_BEARER_TOKEN` from `.env` |
| `Content-Type` | `application/json` |
| `Accept` | `application/json` |

---

## Call 1 — Resolve Cycle

Retrieves the full test cycle tree so the skill can locate the target cycle by its PID (e.g., `CL-416`).

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-cycles` |
| **Query Params** | `expand=descendants` |
| **Success Code** | `200 OK` |
| **Pipeline Position** | First call. Always executed exactly once. |
| **Trigger** | Unconditional — this is the entry point. |

### Full URL Template

```
GET https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-cycles?expand=descendants
```

### Behavior

The response is a tree of cycles. The skill performs a recursive depth-first search through `test_cycles` children looking for a node whose `pid` matches the target (e.g., `CL-416`). Once found, the numeric `id` is extracted and used in subsequent calls.

If the PID is not found in the tree, the pipeline aborts with a 404-equivalent error (see `error-handling.md`).

---

## Call 2 — Get Suites

Fetches all test suites directly under the resolved cycle.

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-suites` |
| **Query Params** | `parentId={cycleId}&parentType=test-cycle` |
| **Success Code** | `200 OK` |
| **Pipeline Position** | Second call. Executed once after the cycle is resolved. |
| **Trigger** | Unconditional — always follows Call 1. |

### Full URL Template

```
GET https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-suites?parentId={cycleId}&parentType=test-cycle
```

### Parameters

| Param | Source | Description |
|-------|--------|-------------|
| `parentId` | `id` from Call 1 result | Numeric ID of the resolved cycle |
| `parentType` | Constant | Always `test-cycle` |

### Behavior

Returns an array of test suite objects. The skill stores each suite's `id`, `pid`, and `name` for downstream use. The count of suites (`N_suites`) directly affects the number of Call 3 invocations.

---

## Call 3 — Get Runs

Fetches test runs under each suite (and directly under the cycle). This call is paginated and repeated for each parent container.

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs` |
| **Query Params** | `parentId={parentId}&parentType={parentType}&page={n}&pageSize=100` |
| **Success Code** | `200 OK` |
| **Pipeline Position** | Third set of calls. Executed once per suite, plus once for the cycle itself. |
| **Trigger** | Called for every suite from Call 2, plus once with `parentType=test-cycle` for runs directly under the cycle. |

### Full URL Template

```
GET https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs?parentId={parentId}&parentType={parentType}&page={n}&pageSize=100
```

### Parameters

| Param | Source | Description |
|-------|--------|-------------|
| `parentId` | Suite `id` from Call 2, or cycle `id` from Call 1 | Numeric ID of the parent container |
| `parentType` | Varies | `test-suite` when fetching runs under a suite; `test-cycle` when fetching runs directly under the cycle |
| `page` | Loop counter | 1-indexed page number, starting at 1 |
| `pageSize` | Constant | `100` (maximum recommended value) |

### Pagination

The skill loops page numbers starting at 1. After each response:
- If the response contains fewer than `pageSize` items, pagination is complete for that parent.
- If the response contains exactly `pageSize` items, increment `page` and fetch again.

Each page counts as one API call.

### Behavior

For each test run in the response, the skill extracts the `id`, `pid`, `name`, and status (see `response-schemas.md` for the status fallback chain). Runs with a status of **Failed** or **Blocked** are flagged for Call 5.

---

## Call 4 — Get Statuses

Fetches the project-level mapping of execution status IDs to human-readable names.

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs/execution-statuses` |
| **Query Params** | None |
| **Success Code** | `200 OK` |
| **Pipeline Position** | Fourth call. Executed exactly once. |
| **Trigger** | Unconditional — always executed. |

### Full URL Template

```
GET https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs/execution-statuses
```

### Behavior

Returns an array of `{id, name}` objects. The skill builds a dictionary mapping numeric IDs to names (e.g., `601 -> "Passed"`, `602 -> "Failed"`). This map is used to resolve any status references that only contain numeric IDs.

---

## Call 5 — Get Failure Logs

Fetches the latest execution log for a specific test run, including detailed step-level results. Only called for runs whose status is **Failed** or **Blocked**.

| Property | Value |
|----------|-------|
| **Method** | `GET` |
| **URL** | `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs/{runId}/test-logs/last-run` |
| **Query Params** | `expand=teststeplog.teststep` |
| **Success Code** | `200 OK` |
| **Pipeline Position** | Fifth set of calls. Executed once per failed/blocked run. |
| **Trigger** | Only called for runs identified as Failed or Blocked in Call 3. |

### Full URL Template

```
GET https://{domain}.qtestnet.com/api/v3/projects/{projectId}/test-runs/{runId}/test-logs/last-run?expand=teststeplog.teststep
```

### Parameters

| Param | Source | Description |
|-------|--------|-------------|
| `runId` | `id` from a failed/blocked run in Call 3 | Numeric ID of the test run |

### Behavior

Returns the most recent execution log for the run, including step-level details when the `expand` parameter is provided. The skill extracts the failure note, timestamps, and the full list of step logs to include in the report's failure analysis section.

A `404` response on this endpoint is **not an error** — it means the run has no execution logs (unexecuted). The skill skips gracefully and moves to the next run.

---

## API Call Count Formula

The total number of HTTP requests the pipeline makes is:

```
total = 1 + 1 + (N_suites + 1) + 1 + N_failed_runs
```

| Component | Count | Source |
|-----------|-------|--------|
| Resolve Cycle | 1 | Call 1 |
| Get Suites | 1 | Call 2 |
| Get Runs | N_suites + 1 | Call 3 (one per suite + one for direct cycle runs). Add more if any suite paginates beyond page 1. |
| Get Statuses | 1 | Call 4 |
| Get Failure Logs | N_failed_runs | Call 5 (one per failed/blocked run) |

### Example

A cycle with **3 suites** and **5 failed runs** (all fits within one page per suite):

```
1 + 1 + (3 + 1) + 1 + 5 = 12 API calls
```

A cycle with **10 suites**, one suite requiring 2 pages, and **20 failed runs**:

```
1 + 1 + (10 + 1 + 1) + 1 + 20 = 35 API calls
```

---

## Rate Limiting

qTest enforces rate limits and signals them via HTTP status:

- **Status code**: `429 Too Many Requests`
- **Header**: `Retry-After: {seconds}` — the number of seconds to wait before retrying.
- **Pipeline behavior**: Wait the indicated duration, retry the same request once. If the retry also returns 429, abort the pipeline.

**All API calls in the pipeline are executed sequentially.** There is no parallelism. This is deliberate to stay within qTest rate limits.

---

## Pagination Note

- Default and recommended `pageSize` is `100`.
- The skill loops until a response returns fewer than `pageSize` items.
- Page numbering is 1-indexed (`page=1` is the first page).
- Pagination applies only to Call 3 (Get Runs). All other calls return complete results in a single response.
