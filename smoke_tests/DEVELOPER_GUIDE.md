# qTest API Smoke Tests — Developer Guide

**Version:** 1.0
**Date:** 2026-03-23
**Author:** Quality Engineering Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites & Setup](#2-prerequisites--setup)
3. [Project Structure](#3-project-structure)
4. [How to Run the Smoke Tests](#4-how-to-run-the-smoke-tests)
5. [Script-by-Script Guide](#5-script-by-script-guide)
6. [Sample Request/Response Schemas](#6-sample-requestresponse-schemas)
7. [Understanding the Outputs](#7-understanding-the-outputs)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Overview

These smoke tests validate connectivity and correct behavior of the qTest Manager REST API v3 endpoints used in our test execution reporting workflow. The primary scenario is:

> Given a Test Cycle PID like **CL-416**, retrieve all Test Suites inside it (TC-970, TC-498, etc.), fetch the Test Runs within each suite, and compute execution statistics (Passed, Failed, Blocked, etc.).

Each script targets a single API capability so you can test endpoints independently. Script `07` ties the full chain together.

**Design decisions:**
- **HTTP client:** `requests` library (not httpx, not the qTest SDK)
- **No SDK:** All calls use raw HTTP via `requests.Session`
- **Auth:** Bearer token passed via header; supports both pre-generated tokens and username/password login
- **Config:** Environment variables loaded from `.env` file via `python-dotenv`

---

## 2. Prerequisites & Setup

### System Requirements

- Python 3.8+
- pip (Python package manager)
- Network access to your qTest instance (`https://{domain}.qtestnet.com`)
- qTest Premium or Elite plan (required for API v3 access)

### Step-by-Step Setup

```bash
# 1. Navigate to the smoke_tests directory
cd smoke_tests/

# 2. (Recommended) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env configuration file
cp .env.example .env

# 5. Edit .env and fill in your values (see below)
```

### Configuring .env

Open `.env` in your editor and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `QTEST_DOMAIN` | Yes (or BASE_URL) | Your qTest subdomain, e.g. `mycompany` for `mycompany.qtestnet.com` |
| `QTEST_BASE_URL` | No | Override if your URL doesn't follow the standard pattern |
| `QTEST_BEARER_TOKEN` | Yes* | API token from qTest Site Admin → Download qTest Resources |
| `QTEST_USERNAME` | Alt* | Email for login-based auth |
| `QTEST_PASSWORD` | Alt* | Password for login-based auth |
| `QTEST_PROJECT_ID` | Yes | Numeric project ID (visible in qTest URL or via `GET /api/v3/projects`) |

*Either `QTEST_BEARER_TOKEN` or both `QTEST_USERNAME` + `QTEST_PASSWORD` are required.

**How to find your Project ID:**
1. Log into qTest Manager
2. Look at the URL: `https://yourco.qtestnet.com/p/12345/...` → Project ID is `12345`
3. Or run `01_test_auth.py` which lists all accessible projects with their IDs

---

## 3. Project Structure

```
smoke_tests/
├── .env.example              # Template — copy to .env and configure
├── .env                      # YOUR configuration (git-ignored)
├── requirements.txt          # Python dependencies (requests, python-dotenv)
├── config.py                 # Shared config, session factory, helpers
├── 01_test_auth.py           # Smoke: authentication & token validation
├── 02_test_get_cycles.py     # Smoke: fetch test cycles, resolve PID
├── 03_test_get_suites.py     # Smoke: fetch test suites under a cycle
├── 04_test_get_runs.py       # Smoke: fetch test runs under a suite/cycle
├── 05_test_execution_statuses.py  # Smoke: get status definitions
├── 06_test_get_logs.py       # Smoke: get test logs / execution results
├── 07_test_full_flow.py      # Integration: full CL-xxx → stats flow
└── DEVELOPER_GUIDE.md        # This file
```

---

## 4. How to Run the Smoke Tests

### Run in sequence (recommended first time)

```bash
# Test 1: Verify authentication works
python 01_test_auth.py

# Test 2: Fetch test cycles (optional: resolve a specific PID)
python 02_test_get_cycles.py
python 02_test_get_cycles.py CL-416

# Test 3: Get test suites under a specific cycle
python 03_test_get_suites.py CL-416

# Test 4: Get test runs under a specific suite
python 04_test_get_runs.py TC-970
python 04_test_get_runs.py CL-416 --cycle    # runs directly under a cycle

# Test 5: Get execution status reference data
python 05_test_execution_statuses.py

# Test 6: Get test logs for a specific run (use numeric ID from test 4 output)
python 06_test_get_logs.py 12345

# Test 7: Full end-to-end flow
python 07_test_full_flow.py CL-416
```

### Quick validation (just auth + statuses)

```bash
python 01_test_auth.py && python 05_test_execution_statuses.py
```

---

## 5. Script-by-Script Guide

### 01_test_auth.py — Authentication

**What it tests:** Can we authenticate and reach the qTest API?

**API called:** `GET /api/v3/projects`

**Inputs:** None (reads config from `.env`)

**Expected output:**
- `[PASS]` message with list of accessible projects
- Shows project IDs and names (you need the ID for `.env`)

**Failure modes:**
- `401 Unauthorized` → bad token or credentials
- `429 Rate Limited` → slow down, try again
- Connection error → check `QTEST_DOMAIN`, network/VPN

---

### 02_test_get_cycles.py — Get Test Cycles & Resolve PID

**What it tests:** Fetching test cycles with and without the `expand=descendants` parameter, and resolving a human-readable PID to a numeric ID.

**APIs called:**
- `GET /api/v3/projects/{projectId}/test-cycles`
- `GET /api/v3/projects/{projectId}/test-cycles?expand=descendants`

**Inputs:** Optional PID argument (e.g. `CL-416`)

**Expected output:**
- List of top-level cycles with PIDs and IDs
- Hierarchy view showing child cycles and suites (when expanded)
- PID → ID resolution result (if argument provided)

---

### 03_test_get_suites.py — Get Test Suites Under a Cycle

**What it tests:** Given a cycle PID, fetches the test suites nested inside it.

**APIs called:**
- `GET .../test-cycles?expand=descendants` (for PID resolution)
- `GET .../test-suites?parentId={cycleId}&parentType=test-cycle`

**Inputs:** Required cycle PID (e.g. `CL-416`)

**Expected output:**
- Table of test suites with PID, ID, and Name
- Full JSON of first suite (for schema reference)

---

### 04_test_get_runs.py — Get Test Runs Under a Suite or Cycle

**What it tests:** Fetching test runs with their execution status.

**APIs called:**
- `GET .../test-runs?parentId={id}&parentType=test-suite` (or `test-cycle`)

**Inputs:** Suite PID (e.g. `TC-970`) or Cycle PID with `--cycle` flag

**Expected output:**
- Table of test runs with PID, ID, Name, Status
- Full JSON of first test run (for schema reference)
- Pagination warning if 100+ results

---

### 05_test_execution_statuses.py — Get Execution Statuses

**What it tests:** Retrieves the project's configured execution statuses.

**API called:** `GET .../test-runs/execution-statuses`

**Inputs:** None

**Expected output:**
- Table of statuses with ID, Name, Color, Default flag
- Full JSON response
- ID → Name mapping dictionary (used for aggregation)

---

### 06_test_get_logs.py — Get Test Logs

**What it tests:** Fetching execution results (test logs) for a specific test run.

**APIs called:**
- `GET .../test-runs/{id}/test-logs/last-run` (latest result)
- `GET .../test-runs/{id}/test-logs/last-run?expand=teststeplog.teststep` (with steps)
- `GET .../test-runs/{id}/test-logs` (full history)

**Inputs:** Numeric test run ID (get from script 04 output)

**Expected output:**
- Latest execution status, timestamps, notes
- Step-level results (if expanded)
- Execution history count

---

### 07_test_full_flow.py — Full End-to-End

**What it tests:** The complete CL-xxx → Suites → Runs → Statistics flow.

**All APIs called in sequence:**
1. Resolve PID → `GET .../test-cycles?expand=descendants`
2. Get suites → `GET .../test-suites?parentId=X&parentType=test-cycle`
3. Get runs → `GET .../test-runs?parentId=Y&parentType=test-suite` (per suite, paginated)
4. Get statuses → `GET .../test-runs/execution-statuses`
5. Aggregate stats (client-side)

**Inputs:** Cycle PID (e.g. `CL-416`)

**Expected output:**
- Overall statistics table (Status / Count / Percentage)
- Per-suite breakdown matrix
- JSON output suitable for agent skill consumption

---

## 6. Sample Request/Response Schemas

### Authentication — GET /api/v3/projects

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
Accept: application/json
```

**Response (200 OK):**
```json
[
  {
    "id": 12345,
    "name": "My QA Project",
    "description": "Main testing project",
    "status_id": 1,
    "start_date": "2025-01-01T00:00:00.000+0000",
    "end_date": "2026-12-31T00:00:00.000+0000",
    "admins": ["admin@company.com"],
    "sample": false
  }
]
```

---

### Test Cycle — GET /api/v3/projects/{projectId}/test-cycles/{id}

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-cycles/67890 HTTP/1.1
Authorization: Bearer {token}
Accept: application/json
```

**Response (200 OK):**
```json
{
  "id": 67890,
  "pid": "CL-416",
  "name": "Sprint 42 Regression Cycle",
  "order": 1,
  "description": "Full regression for Sprint 42 release",
  "web_url": "https://yourco.qtestnet.com/p/12345/portal/project#tab=testexecution&object=2&id=67890",
  "created_date": "2026-03-01T10:00:00.000+0000",
  "last_modified_date": "2026-03-20T15:30:00.000+0000",
  "links": [
    {
      "rel": "self",
      "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-cycles/67890"
    },
    {
      "rel": "test-suites",
      "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-suites?parentId=67890&parentType=test-cycle"
    },
    {
      "rel": "test-runs",
      "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-runs?parentId=67890&parentType=test-cycle"
    }
  ]
}
```

---

### Test Cycle with Descendants — GET .../test-cycles?expand=descendants

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-cycles?expand=descendants HTTP/1.1
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 67890,
    "pid": "CL-416",
    "name": "Sprint 42 Regression Cycle",
    "order": 1,
    "description": "Full regression for Sprint 42 release",
    "web_url": "https://yourco.qtestnet.com/p/12345/...",
    "test_cycles": [
      {
        "id": 67891,
        "pid": "CL-417",
        "name": "Sub-cycle: API Tests",
        "test_cycles": [],
        "test_suites": [
          {
            "id": 54323,
            "pid": "TC-501",
            "name": "API Smoke Suite"
          }
        ]
      }
    ],
    "test_suites": [
      {
        "id": 54321,
        "pid": "TC-970",
        "name": "Smoke Tests"
      },
      {
        "id": 54322,
        "pid": "TC-498",
        "name": "Regression Suite"
      }
    ]
  }
]
```

**Key insight:** The `expand=descendants` response nests `test_cycles` and `test_suites` arrays inside each cycle object, giving you the full tree in one call.

---

### Test Suite — GET .../test-suites?parentId={cycleId}&parentType=test-cycle

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-suites?parentId=67890&parentType=test-cycle HTTP/1.1
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 54321,
    "pid": "TC-970",
    "name": "Smoke Tests",
    "order": 1,
    "description": "Core smoke test suite",
    "web_url": "https://yourco.qtestnet.com/p/12345/...",
    "created_date": "2026-03-01T10:30:00.000+0000",
    "last_modified_date": "2026-03-18T12:00:00.000+0000",
    "properties": [],
    "links": [
      {
        "rel": "self",
        "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-suites/54321"
      },
      {
        "rel": "test-runs",
        "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-runs?parentId=54321&parentType=test-suite"
      }
    ]
  },
  {
    "id": 54322,
    "pid": "TC-498",
    "name": "Regression Suite",
    "order": 2,
    "description": "",
    "web_url": "https://yourco.qtestnet.com/p/12345/...",
    "properties": [],
    "links": [...]
  }
]
```

---

### Test Runs — GET .../test-runs?parentId={suiteId}&parentType=test-suite

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-runs?parentId=54321&parentType=test-suite&page=1&pageSize=100 HTTP/1.1
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 98765,
    "pid": "TR-1001",
    "name": "Verify login with valid credentials",
    "order": 1,
    "created_date": "2026-03-01T11:00:00.000+0000",
    "last_modified_date": "2026-03-19T09:15:00.000+0000",
    "web_url": "https://yourco.qtestnet.com/p/12345/...",
    "test_case": {
      "id": 44556,
      "pid": "TS-200",
      "name": "Login - valid credentials"
    },
    "test_case_version_id": 44557,
    "properties": [
      {
        "field_id": 12340001,
        "field_name": "Status",
        "field_value": "601",
        "field_value_name": "Passed"
      },
      {
        "field_id": 12340002,
        "field_name": "Assigned To",
        "field_value": "user@company.com",
        "field_value_name": "John Doe"
      },
      {
        "field_id": 12340003,
        "field_name": "Planned Start Date",
        "field_value": "2026-03-15T00:00:00.000+0000"
      }
    ],
    "links": [
      {
        "rel": "test-logs",
        "href": "https://yourco.qtestnet.com/api/v3/projects/12345/test-runs/98765/test-logs"
      }
    ]
  },
  {
    "id": 98766,
    "pid": "TR-1002",
    "name": "Verify login with invalid password",
    "properties": [
      {
        "field_id": 12340001,
        "field_name": "Status",
        "field_value": "602",
        "field_value_name": "Failed"
      }
    ],
    "links": [...]
  }
]
```

**Key insight:** Status lives inside the `properties` array. Look for `field_name == "Status"` and read `field_value_name` for the display name, or `field_value` for the status ID (which maps to the execution statuses endpoint).

---

### Execution Statuses — GET .../test-runs/execution-statuses

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-runs/execution-statuses HTTP/1.1
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
[
  {
    "id": 601,
    "name": "Passed",
    "color": "#6cc644",
    "is_default": false
  },
  {
    "id": 602,
    "name": "Failed",
    "color": "#d0021b",
    "is_default": false
  },
  {
    "id": 603,
    "name": "Incomplete",
    "color": "#f5a623",
    "is_default": false
  },
  {
    "id": 604,
    "name": "Blocked",
    "color": "#8b572a",
    "is_default": false
  },
  {
    "id": 605,
    "name": "Unexecuted",
    "color": "#999999",
    "is_default": true
  }
]
```

**Note:** Your project may have additional custom statuses. The `is_default: true` status is automatically assigned to newly created test runs.

---

### Test Log (Latest) — GET .../test-runs/{id}/test-logs/last-run

**Request:**
```http
GET https://yourco.qtestnet.com/api/v3/projects/12345/test-runs/98765/test-logs/last-run?expand=teststeplog.teststep HTTP/1.1
Authorization: Bearer {token}
```

**Response (200 OK):**
```json
{
  "id": 777001,
  "test_run_id": 98765,
  "status": {
    "id": 601,
    "name": "Passed",
    "color": "#6cc644",
    "is_default": false
  },
  "exe_start_date": "2026-03-19T09:00:00.000+0000",
  "exe_end_date": "2026-03-19T09:15:00.000+0000",
  "note": "All steps passed. Verified on Chrome 120.",
  "build_number": "v3.2.1",
  "build_url": "",
  "attachments": [],
  "test_step_logs": [
    {
      "id": 888001,
      "test_step_id": 99001,
      "order": 0,
      "status": "Passed",
      "description": "Navigate to login page",
      "expected_result": "Login page loads",
      "actual_result": "Login page loaded successfully",
      "note": ""
    },
    {
      "id": 888002,
      "test_step_id": 99002,
      "order": 1,
      "status": "Passed",
      "description": "Enter valid username and password",
      "expected_result": "Credentials accepted",
      "actual_result": "Fields populated, submit enabled",
      "note": ""
    }
  ]
}
```

**Response (404 Not Found)** — when the test run has never been executed:
```json
{
  "message": "Test Log not found"
}
```

---

### Error Responses

**401 Unauthorized:**
```json
{
  "message": "Unauthorized"
}
```

**404 Not Found:**
```json
{
  "message": "Object not found"
}
```

**429 Rate Limited:**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
```

---

## 7. Understanding the Outputs

### Script 07 Output — Statistics Table

The full flow script produces a table like:

```
  ┌─────────────────────────────────────────────────┐
  │  OVERALL STATISTICS for CL-416                  │
  ├─────────────────────────────────────────────────┤
  │  Total Test Runs: 61                            │
  ├──────────────────────┬──────────┬───────────────┤
  │  Status              │  Count   │  Percentage   │
  ├──────────────────────┼──────────┼───────────────┤
  │  Blocked             │  2       │    3.3%       │
  │  Failed              │  5       │    8.2%       │
  │  Incomplete          │  1       │    1.6%       │
  │  Passed              │  45      │   73.8%       │
  │  Unexecuted          │  8       │   13.1%       │
  └──────────────────────┴──────────┴───────────────┘
```

It also outputs a JSON blob suitable for consumption by an AI agent skill:

```json
{
  "cycle_pid": "CL-416",
  "cycle_id": 67890,
  "cycle_name": "Sprint 42 Regression Cycle",
  "total_runs": 61,
  "overall_stats": {
    "Passed": 45,
    "Failed": 5,
    "Blocked": 2,
    "Incomplete": 1,
    "Unexecuted": 8
  },
  "suites": [
    {"pid": "TC-970", "id": 54321, "name": "Smoke Tests", "run_count": 25},
    {"pid": "TC-498", "id": 54322, "name": "Regression Suite", "run_count": 36}
  ]
}
```

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `CONFIGURATION ERROR` on startup | Missing `.env` values | Run `cp .env.example .env` and fill in values |
| `401 Unauthorized` | Bad token or expired session | Regenerate token from qTest Site Admin |
| `403 Forbidden` | Insufficient permissions | Contact qTest admin to grant API access |
| `404 Not Found` on cycle/suite | Wrong Project ID or PID doesn't exist | Verify `QTEST_PROJECT_ID`; run script 02 to list available PIDs |
| `429 Too Many Requests` | Rate limited | Wait 60 seconds; reduce call frequency |
| `ConnectionError` | Network/VPN issue | Check VPN connection; verify domain resolves |
| Empty results from test-suites | Suites may be nested in sub-cycles | Use `expand=descendants` on cycle; check sub-cycles |
| Status shows as "Unknown" | Properties format varies by qTest version | Check raw JSON output; status field name may differ |
| Pagination missed data | Default page size is 100 | Script 07 handles pagination; others show page 1 only |
