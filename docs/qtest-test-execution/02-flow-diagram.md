# Add Test Cases to Suite — Flow Diagram

```mermaid
flowchart TD
    START([Start]) --> ENV

    ENV["Load credentials from .env
    ─────────────────────────
    QTEST_DOMAIN
    QTEST_BEARER_TOKEN
    QTEST_PROJECT_ID"]

    ENV --> KNOW_SUITE{Know the\nTest Suite ID?}

    KNOW_SUITE -- Yes --> GET_MODULE
    KNOW_SUITE -- No --> GET_CYCLES

    GET_CYCLES["GET /api/v3/projects/{projectId}/test-cycles
    ──────────────────────────────────────────
    Returns: list of cycles with id, name, pid"]

    GET_CYCLES --> GET_SUITES

    GET_SUITES["GET /api/v3/projects/{projectId}/test-suites
    ?parentId={testCycleId}&parentType=test-cycle
    ──────────────────────────────────────────────
    Returns: list of suites — grab numeric id"]

    GET_SUITES --> GET_MODULE

    GET_MODULE["GET /api/v3/projects/{projectId}/test-cases
    ?parentId={moduleId}
    ──────────────────────────────────────────
    Returns: list of test cases in the module"]

    GET_MODULE --> EXTRACT["Extract numeric id from each test case
    ─────────────────────────────────────────
    [ 111, 222, 333, 444, 555 ]"]

    EXTRACT --> DEDUP{Check for\nduplicates\nin suite?}

    DEDUP -- Yes --> GET_EXISTING

    GET_EXISTING["GET /api/v3/projects/{projectId}/test-runs
    ?parentId={testSuiteId}&parentType=test-suite
    ─────────────────────────────────────────────
    Returns: existing runs — extract testCaseId set"]

    GET_EXISTING --> FILTER["Filter out IDs already present in suite
    ─────────────────────────────────────────
    new_ids = all_ids - existing_ids"]

    FILTER --> LOOP

    DEDUP -- No --> LOOP

    LOOP{"More test\ncase IDs?"}

    LOOP -- Yes --> POST

    POST["POST /api/v3/projects/{projectId}/test-runs
    ?parentId={testSuiteId}&parentType=test-suite
    ─────────────────────────────────────────────
    Body: { test_case: { id: 111 }, properties: [] }"]

    POST --> CHECK_RESP{HTTP\nstatus?}

    CHECK_RESP -- 201 Created --> LOG["Log: Created TR-n for TC id
    ────────────────────────────
    Response includes pid, id, name"]

    LOG --> LOOP

    CHECK_RESP -- 401 --> ERR_401["Expired token
    ─────────────
    Regenerate QTEST_BEARER_TOKEN"]

    CHECK_RESP -- 404 --> ERR_404["Bad suite ID or TC ID
    ──────────────────────
    Re-query modules and suites"]

    CHECK_RESP -- 400 --> ERR_400["Missing required field
    ───────────────────────
    Check test_case.id and properties"]

    ERR_401 --> END_ERR([Stop])
    ERR_404 --> END_ERR
    ERR_400 --> END_ERR

    LOOP -- No --> DONE(["Done — all test runs created in suite"])
```

---

## Key Decision Points

| Diamond | What it controls |
|---|---|
| **Know the Test Suite ID?** | Skip the cycle/suite lookup if ID is already known or hardcoded in `.env` |
| **Check for duplicates?** | Optional guard — skip if you know the suite is empty or don't mind duplicates |
| **More test case IDs?** | Loop continues until all IDs have been posted |
| **HTTP status?** | Determines success path vs error branch |

## Data Flow Summary

```
.env
 └─► BASE_URL + AUTH HEADERS
      │
      ├─► [optional] /test-cycles → /test-suites → testSuiteId
      │
      ├─► /test-cases?parentId={moduleId} → [ id, id, id, ... ]
      │
      ├─► [optional] /test-runs?parentId={suiteId} → existing ids → filter
      │
      └─► loop: POST /test-runs (one per id) → TR-1, TR-2, TR-3, ...
```
