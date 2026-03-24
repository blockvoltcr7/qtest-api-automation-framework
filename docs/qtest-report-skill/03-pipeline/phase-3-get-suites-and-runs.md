# Phase 3: Get Suites & Runs

## Purpose

Given a resolved `cycle_id` from Phase 2, fetch all test suites under that cycle and all test runs within each suite. Also fetches any test runs placed directly under the cycle (not inside any suite).

---

## API Calls

### API Call A: Get Test Suites

```
GET /api/v3/projects/{projectId}/test-suites?parentId={cycleId}&parentType=test-cycle
```

Returns an array of test suite objects. From each suite, we extract:
- `id` -- numeric ID, used to query runs within the suite
- `pid` -- display PID like "TS-970", used in the report
- `name` -- human-readable suite name

**Code reference**: `get_test_suites()` from `smoke_tests/07_test_full_flow.py` lines 45-52

```python
def get_test_suites(session, api_base, cycle_id):
    """Get all test suites under a test cycle."""
    resp = session.get(
        f"{api_base}/test-suites",
        params={"parentId": cycle_id, "parentType": "test-cycle"},
    )
    resp.raise_for_status()
    return resp.json()
```

---

### API Call B: Get Test Runs per Suite (paginated)

```
GET /api/v3/projects/{projectId}/test-runs?parentId={suiteId}&parentType=test-suite&page={n}&pageSize=100
```

This call is made once per suite, with pagination. The pagination loop continues until a page returns fewer items than `pageSize`.

**Code reference**: `get_test_runs_paginated()` from `smoke_tests/07_test_full_flow.py` lines 55-85

```python
def get_test_runs_paginated(session, api_base, parent_id, parent_type, page_size=100):
    """Get ALL test runs under a parent, handling pagination."""
    all_runs = []
    page = 1

    while True:
        resp = session.get(
            f"{api_base}/test-runs",
            params={
                "parentId": parent_id,
                "parentType": parent_type,
                "page": page,
                "pageSize": page_size,
            },
        )
        resp.raise_for_status()
        runs = resp.json()

        if not runs:
            break

        all_runs.extend(runs)

        if len(runs) < page_size:
            break  # Last page
        page += 1

    return all_runs
```

### Pagination Logic

The qTest API does not return a total count or "has more" flag in the test-runs endpoint. Instead, pagination is detected by comparing the number of results to the requested page size:

```
Request page 1 (pageSize=100) -> 100 results  -> more pages exist, request page 2
Request page 2 (pageSize=100) -> 100 results  -> more pages exist, request page 3
Request page 3 (pageSize=100) ->  47 results  -> 47 < 100, this is the last page
```

If a page returns an empty array, that also terminates the loop.

---

### API Call C: Get Direct Runs Under Cycle

```
GET /api/v3/projects/{projectId}/test-runs?parentId={cycleId}&parentType=test-cycle
```

Test runs can be placed directly under a test cycle without being inside any suite. These runs use the same paginated fetch but with `parentType=test-cycle`.

```python
# From 07_test_full_flow.py lines 182-186
direct_runs = get_test_runs_paginated(session, api_base, cycle_id, "test-cycle")
if direct_runs:
    suite_runs["(direct under cycle)"] = direct_runs
    all_runs.extend(direct_runs)
```

---

## Input

- `cycle_id`: int, from Phase 2
- `session`: authenticated `requests.Session`
- `api_base`: project API base URL

---

## Output

A dictionary mapping suite identifiers to their test run arrays:

```python
{
    "TS-970": [
        {"id": 1001, "pid": "TR-1001", "name": "Verify login", ...},
        {"id": 1002, "pid": "TR-1002", "name": "Verify logout", ...},
        # ... more runs
    ],
    "TS-971": [
        {"id": 2001, "pid": "TR-2001", "name": "Create order", ...},
        # ... more runs
    ],
    "(direct)": [
        {"id": 3001, "pid": "TR-3001", "name": "Standalone test", ...},
    ]
}
```

Each test run object is the full JSON returned by the qTest API, including `properties`, `latest_test_log`, and other fields used in Phase 4.

---

## Performance Characteristics

### API Call Count Formula

```
calls = 1 (suites) + sum(ceil(runs_per_suite / 100) for each suite) + ceil(direct_runs / 100)
```

### Typical Scenarios

| Scenario | Suites | Runs/Suite | Direct Runs | Total API Calls |
|----------|--------|------------|-------------|-----------------|
| Small cycle | 2 | ~20 each | 0 | 1 + 2 + 0 = 3 |
| Medium cycle | 5 | ~40 each | 5 | 1 + 5 + 1 = 7 |
| Large cycle | 10 | ~100 each | 0 | 1 + 10 + 0 = 11 |
| Very large suite | 1 | 500 | 0 | 1 + 5 + 0 = 6 |

For the expected use case (5 suites, ~200 total runs), expect **5-8 API calls**.

---

## Pseudocode

```
FUNCTION get_suites_and_runs(session, api_base, cycle_id):
    # Step A: Get all suites
    suites = GET /test-suites?parentId={cycle_id}&parentType=test-cycle

    suite_runs = {}
    all_runs = []
    suite_metadata = []

    # Step B: Get runs for each suite
    FOR each suite IN suites:
        runs = get_test_runs_paginated(session, api_base, suite.id, "test-suite")
        suite_runs[suite.pid] = runs
        all_runs.extend(runs)
        suite_metadata.append({
            "id": suite.id,
            "pid": suite.pid,
            "name": suite.name,
            "run_count": len(runs)
        })

    # Step C: Get runs directly under the cycle
    direct_runs = get_test_runs_paginated(session, api_base, cycle_id, "test-cycle")
    IF direct_runs:
        suite_runs["(direct)"] = direct_runs
        all_runs.extend(direct_runs)

    RETURN suite_runs, all_runs, suite_metadata
```

---

## Edge Cases

### Empty Cycle (0 suites)

If the suites endpoint returns an empty array, the pipeline continues normally. The report will show:

- 0 suites listed
- Only direct runs (if any) are counted
- If there are also 0 direct runs, the report states "No test suites or runs found under CL-416"

This is graceful -- the pipeline does not abort.

### Suite with 0 Runs

A suite that exists but has no test runs is included in the report with a count of 0. This is meaningful information: it tells the team that the suite was created but no tests have been assigned or executed.

```json
{
    "pid": "TS-999",
    "name": "Performance Tests",
    "total": 0,
    "passed": 0,
    "failed": 0,
    "pass_rate": null
}
```

Note: `pass_rate` is `null` (not 0) when there are no executed runs, since division by zero is undefined.

### Suite with 500+ Runs

Pagination handles this automatically. With `pageSize=100`, a suite with 500 runs requires 5 API calls:

```
Page 1: 100 runs
Page 2: 100 runs
Page 3: 100 runs
Page 4: 100 runs
Page 5: 100 runs (len == pageSize, so check page 6)
Page 6: 0 runs   (empty array, stop)
```

Or if there are exactly 500:
```
Page 5: 100 runs (len == pageSize, check page 6)
Page 6: 0 runs (stop)
```

This is safe and bounded. The worst case for a single suite is `ceil(n/100) + 1` calls.

### Rate Limiting

qTest Manager does not heavily rate-limit API calls in typical deployments, but for very large cycles (20+ suites, 1000+ runs), the sequential nature of the calls provides natural throttling. No explicit rate-limiting or delay logic is needed for the expected use case.

If rate limiting becomes an issue, the pagination loop's sequential nature means only one call is in-flight at a time, which is the most conservative approach possible.

---

## Test Run Object Structure

Each test run returned by the API includes fields used in Phase 4. Key fields:

```json
{
    "id": 1001,
    "pid": "TR-1001",
    "name": "Verify login with valid credentials",
    "order": 1,
    "properties": [
        {
            "field_name": "Status",
            "field_value": "602",
            "field_value_name": "Passed"
        }
    ],
    "latest_test_log": {
        "status": {
            "id": 602,
            "name": "Passed"
        },
        "exe_start_date": "2026-03-22T14:00:00Z",
        "exe_end_date": "2026-03-22T14:02:30Z"
    },
    "exe_status": 602
}
```

Not all fields are always present -- Phase 4's status extraction uses a 3-fallback strategy to handle this variation.
