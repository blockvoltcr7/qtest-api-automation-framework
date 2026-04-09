# Add Existing Test Cases to a Test Suite

## Overview

This guide covers the full workflow for taking existing test cases from a module folder and adding them to a test suite in qTest Test Execution. Each test case becomes a **test run** — the execution instance linking Test Design to Test Execution.

```
Test Design:   Module → Test Cases (the source)
Test Execution: Cycle → Test Suite → Test Runs (the destination)
```

---

## What You Need Before Making Any Calls

| Piece of data | How to get it |
|---|---|
| `moduleId` | `GET /api/v3/projects/{projectId}/modules?expand=descendants` — see `02-modules-api.md` |
| `testCycleId` | `GET /api/v3/projects/{projectId}/test-cycles` |
| `testSuiteId` | `GET /api/v3/projects/{projectId}/test-suites?parentId={testCycleId}&parentType=test-cycle` |
| Test case numeric `id`s | `GET /api/v3/projects/{projectId}/test-cases?parentId={moduleId}` |
| Bearer token, project ID | `.env` file |

> **Note:** `testSuiteId` is the numeric integer ID, not the display PID (e.g. not `TS-5`). Most teams hardcode this or store it in `.env` rather than resolve it dynamically every run.

---

## Step 1 — Get Test Case IDs from a Module

```
GET /api/v3/projects/{projectId}/test-cases?parentId={moduleId}
Authorization: Bearer {token}
```

### Response (200 OK)

```json
[
  {
    "id": 111,
    "pid": "TC-10",
    "name": "Verify login with valid credentials",
    "parent_id": 2107619
  },
  {
    "id": 222,
    "pid": "TC-11",
    "name": "Verify login with invalid password",
    "parent_id": 2107619
  }
]
```

Extract the numeric `id` field from each entry — **not** the `pid` string.

### curl Example

```bash
curl -s \
  "https://${QTEST_DOMAIN}.qtestnet.com/api/v3/projects/${QTEST_PROJECT_ID}/test-cases?parentId=${MODULE_ID}" \
  -H "Authorization: Bearer ${QTEST_BEARER_TOKEN}" \
  | jq '[.[] | {id, pid, name}]'
```

---

## Step 2 — Resolve the Test Suite ID (if unknown)

### 2a. List Test Cycles

```
GET /api/v3/projects/{projectId}/test-cycles
Authorization: Bearer {token}
```

```json
[
  { "id": 500001, "name": "Sprint 12", "pid": "CL-1" }
]
```

### 2b. List Test Suites in a Cycle

```
GET /api/v3/projects/{projectId}/test-suites?parentId={testCycleId}&parentType=test-cycle
Authorization: Bearer {token}
```

```json
[
  { "id": 843974, "name": "Smoke Tests", "pid": "TS-5" },
  { "id": 843975, "name": "Regression Tests", "pid": "TS-6" }
]
```

Use the numeric `id` (e.g. `843974`) as `parentId` in Step 3.

---

## Step 3 — Create a Test Run (one per test case)

There is no batch endpoint for adding multiple distinct test cases at once. Make one call per test case.

```
POST /api/v3/projects/{projectId}/test-runs?parentId={testSuiteId}&parentType=test-suite
Authorization: Bearer {token}
Content-Type: application/json
```

### Query Parameters

| Param | Required | Value |
|---|---|---|
| `parentId` | Yes | Numeric test suite ID |
| `parentType` | Yes | `"test-suite"` |

### Request Body

```json
{
  "test_case": { "id": 111 },
  "properties": []
}
```

### Request Body Fields

| Field | Required | Notes |
|---|---|---|
| `test_case.id` | Yes | Numeric ID of the existing test case — **not** the PID |
| `properties` | Yes | Custom field values. Pass `[]` if none required. |
| `name` | No | Display name for the run. Defaults to the test case name. |
| `test_case_version_id` | No | Pin to a specific TC version. Omit to use latest. |

### Success Response (201 Created)

```json
{
  "id": 11595056,
  "pid": "TR-2",
  "name": "Verify login with valid credentials",
  "parentId": 843974,
  "parentType": "test-suite",
  "testCaseId": 111,
  "test_case_version": "1.0",
  "created_date": "2026-04-09T10:00:00.000Z"
}
```

### curl Example (single test case)

```bash
curl -s -X POST \
  "https://${QTEST_DOMAIN}.qtestnet.com/api/v3/projects/${QTEST_PROJECT_ID}/test-runs?parentId=${TEST_SUITE_ID}&parentType=test-suite" \
  -H "Authorization: Bearer ${QTEST_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{ "test_case": { "id": 111 }, "properties": [] }'
```

---

## Full Workflow — Python Example

```python
from dotenv import load_dotenv
import os
import requests

load_dotenv()

BASE_URL = f"https://{os.getenv('QTEST_DOMAIN')}.qtestnet.com"
PROJECT_ID = os.getenv("QTEST_PROJECT_ID")
HEADERS = {
    "Authorization": f"Bearer {os.getenv('QTEST_BEARER_TOKEN')}",
    "Content-Type": "application/json"
}


def get_test_case_ids(module_id: int) -> list[int]:
    """Fetch all test case numeric IDs from a module folder."""
    r = requests.get(
        f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/test-cases",
        params={"parentId": module_id},
        headers=HEADERS
    )
    r.raise_for_status()
    return [tc["id"] for tc in r.json()]


def add_to_suite(test_suite_id: int, test_case_ids: list[int]) -> list[dict]:
    """
    Add a list of existing test cases to a test suite.
    Returns a list of created test run objects.
    """
    created_runs = []
    for tc_id in test_case_ids:
        r = requests.post(
            f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/test-runs",
            params={"parentId": test_suite_id, "parentType": "test-suite"},
            headers=HEADERS,
            json={"test_case": {"id": tc_id}, "properties": []}
        )
        r.raise_for_status()
        run = r.json()
        print(f"Created {run['pid']} for TC {tc_id}")
        created_runs.append(run)
    return created_runs


# Example: add all test cases from module 2107619 to suite 843974
tc_ids = get_test_case_ids(module_id=2107619)
runs = add_to_suite(test_suite_id=843974, test_case_ids=tc_ids)
print(f"Added {len(runs)} test runs to suite.")
```

---

## What a 5-Test-Case Request Sequence Looks Like

```
POST /test-runs?parentId=843974&parentType=test-suite  body: { "test_case": { "id": 111 } }  → TR-10
POST /test-runs?parentId=843974&parentType=test-suite  body: { "test_case": { "id": 222 } }  → TR-11
POST /test-runs?parentId=843974&parentType=test-suite  body: { "test_case": { "id": 333 } }  → TR-12
POST /test-runs?parentId=843974&parentType=test-suite  body: { "test_case": { "id": 444 } }  → TR-13
POST /test-runs?parentId=843974&parentType=test-suite  body: { "test_case": { "id": 555 } }  → TR-14
```

Five test cases = five calls. Each call is synchronous and returns immediately with the created test run.

---

## Avoiding Duplicates

qTest does **not** deduplicate — calling this twice creates duplicate test runs in the suite. To guard against this, check what already exists before adding:

```python
def get_existing_tc_ids_in_suite(test_suite_id: int) -> set[int]:
    """Return set of testCaseIds already in the suite."""
    r = requests.get(
        f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/test-runs",
        params={"parentId": test_suite_id, "parentType": "test-suite"},
        headers=HEADERS
    )
    r.raise_for_status()
    return {run["testCaseId"] for run in r.json()}

existing = get_existing_tc_ids_in_suite(843974)
new_ids = [tc_id for tc_id in tc_ids if tc_id not in existing]
add_to_suite(843974, new_ids)
```

---

## Error Reference

| Code | Cause | Fix |
|---|---|---|
| `401` | Expired token | Regenerate `QTEST_BEARER_TOKEN` |
| `403` | No access to project or suite | Check project ID and user role |
| `404` | Invalid `parentId` or `test_case.id` | Re-query test cases and suites to verify IDs |
| `400` | Missing required field | Ensure `test_case.id` and `properties` are present |
