# Knowledge Transfer Document

## qTest API Integration for Test Execution Reporting

**Quality Engineering Team**
**Version 1.0 | March 2026**

**Prepared by:** Quality Engineering Team
**Audience:** Development Team, QA Engineers, DevOps
**Purpose:** Enable team to implement and run qTest API smoke tests locally

---

## 1. Executive Summary

This document provides the knowledge transfer package for integrating with the Tricentis qTest Manager REST API (v3) to retrieve test execution data. The package includes Python smoke test scripts that validate each API endpoint, a shared configuration module, and comprehensive documentation of request/response schemas.

The primary use case is: given a Test Cycle PID (e.g. CL-416), retrieve all Test Suites inside it, fetch the Test Runs within each suite, and compute execution statistics (Passed, Failed, Blocked, etc.). This workflow will eventually power AI agent skills for GitHub Copilot CLI.

---

## 2. Architecture Overview

The solution uses Python 3.8+ with the `requests` library to make direct HTTP calls to the qTest v3 REST API. No qTest SDK is used. All configuration is loaded from environment variables via `python-dotenv`.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| HTTP Client: `requests` | Industry standard, team familiarity, no async needed for this workflow |
| No qTest SDK | Direct API control, fewer dependencies, easier to adapt to agent skills |
| Bearer token auth | Pre-generated tokens from qTest admin are simplest; username/password login also supported |
| Client-side stats | qTest has no statistics endpoint; we aggregate test run statuses in Python |
| Pagination handling | API defaults to 100 results per page (max ~999); full flow script loops pages |

---

## 3. Package Contents

The `smoke_tests/` directory in your workspace contains the following files:

| File | Purpose |
|------|---------|
| `.env.example` | Template configuration file — copy to `.env` and fill in your values |
| `requirements.txt` | Python dependencies (`requests`, `python-dotenv`) |
| `config.py` | Shared module: config loader, session factory with auth, response printer |
| `01_test_auth.py` | Smoke test: validate authentication and list accessible projects |
| `02_test_get_cycles.py` | Smoke test: fetch test cycles, demonstrate PID → ID resolution |
| `03_test_get_suites.py` | Smoke test: fetch test suites under a given test cycle |
| `04_test_get_runs.py` | Smoke test: fetch test runs under a suite or cycle |
| `05_test_execution_statuses.py` | Smoke test: retrieve execution status definitions (Passed, Failed, etc.) |
| `06_test_get_logs.py` | Smoke test: fetch test logs (latest execution result, history) |
| `07_test_full_flow.py` | Integration test: full CL-xxx → Suites → Runs → Statistics flow |
| `DEVELOPER_GUIDE.md` | Detailed guide with request/response schemas and troubleshooting |

---

## 4. How to Set Up on Your Local Machine

### Prerequisites

- Python 3.8 or higher installed
- pip (Python package manager)
- Network access to your qTest instance (VPN if required)
- qTest Premium or Elite plan (required for API v3 access)
- A qTest API Bearer token (from Site Admin → Download qTest Resources)

### Step-by-Step Setup

1. Clone or copy the `smoke_tests/` directory to your local machine
2. Open a terminal and navigate to the `smoke_tests/` directory
3. Create a Python virtual environment: `python3 -m venv .venv`
4. Activate it: `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`
6. Copy the environment template: `cp .env.example .env`
7. Edit `.env` with your qTest domain, Bearer token, and Project ID
8. Run the auth test to verify: `python 01_test_auth.py`

**Finding your Project ID:** Log into qTest Manager and look at the URL. It follows the pattern `https://yourco.qtestnet.com/p/12345/...` where `12345` is your numeric Project ID. Alternatively, run `01_test_auth.py` which lists all accessible projects with their IDs.

---

## 5. API Call Flow

The following table shows the complete API call chain for the primary scenario (Test Cycle → Statistics):

| Step | API Endpoint | Purpose |
|------|-------------|---------|
| 1 | `POST /oauth/token` | Authenticate and get Bearer token (or use pre-generated token) |
| 2 | `GET .../test-cycles?expand=descendants` | Fetch all cycles with children; find CL-416 by pid field to get numeric ID |
| 3 | `GET .../test-suites?parentId=X&parentType=test-cycle` | Get test suites (TC-970, TC-498, etc.) nested under the cycle |
| 4 | `GET .../test-runs?parentId=Y&parentType=test-suite` | For each suite, get all test runs (paginated — loop if 100+ results) |
| 5 | `GET .../test-runs/execution-statuses` | Get the status ID → name mapping (Passed, Failed, Blocked, etc.) |
| 6 | Client-side aggregation | Count test runs by status to produce statistics output |

---

## 6. qTest Identifier Reference

qTest uses human-readable PIDs (prefixed identifiers) alongside numeric internal IDs. The API endpoints require numeric IDs, but responses include both.

| Prefix | Object Type | Example | API Endpoint Pattern |
|--------|-------------|---------|---------------------|
| `CL-` | Test Cycle | CL-416 | `/test-cycles/{id}` |
| `TC-` | Test Suite | TC-970 | `/test-suites/{id}` |
| `TR-` | Test Run | TR-1234 | `/test-runs/{id}` |
| `TS-` | Test Case | TS-5678 | `/test-cases/{id}` |
| `RQ-` | Requirement | RQ-100 | `/requirements/{id}` |

---

## 7. Running the Smoke Tests

### Recommended First-Time Sequence

Run the scripts in order. Each builds on information from the previous one:

| Order | Command | What You Learn |
|-------|---------|---------------|
| 1st | `python 01_test_auth.py` | Token works; get your Project ID |
| 2nd | `python 02_test_get_cycles.py` | See all cycle PIDs available |
| 3rd | `python 02_test_get_cycles.py CL-416` | Resolve CL-416 to numeric ID |
| 4th | `python 03_test_get_suites.py CL-416` | See all suites in the cycle |
| 5th | `python 04_test_get_runs.py TC-970` | See test runs with status |
| 6th | `python 05_test_execution_statuses.py` | Get status reference mapping |
| 7th | `python 06_test_get_logs.py 12345` | Detailed execution logs |
| 8th | `python 07_test_full_flow.py CL-416` | Full statistics output |

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| CONFIGURATION ERROR | Missing `.env` values | Copy `.env.example` to `.env` and fill in all required fields |
| 401 Unauthorized | Bad or expired token | Regenerate API token from qTest Site Admin → Download qTest Resources |
| 403 Forbidden | Insufficient permissions | Contact qTest admin to grant API access to your account |
| 404 Not Found | Wrong Project ID or PID | Verify `QTEST_PROJECT_ID`; run script 02 to see available PIDs |
| 429 Too Many Requests | Rate limited | Wait 60 seconds between runs; reduce call frequency |
| ConnectionError | Network / VPN issue | Check VPN connection; verify domain resolves with ping |
| Empty test suites list | Suites in sub-cycles | Use `expand=descendants`; check nested child cycles |
| Status = "Unknown" | Properties format varies | Check raw JSON output; status field name may differ by qTest version |

---

## 9. Next Steps

Once the team has validated the smoke tests against our qTest instance, the following next steps are planned:

- **Build a reusable QTestClient class** that encapsulates the session, PID resolution, pagination, and retry logic into a clean Python module.

- **Create agent skills** for GitHub Copilot CLI that use the QTestClient to answer natural language queries like "What's the status of CL-416?"

- **Add caching layer** to avoid hitting the API repeatedly for the same data within a session.

- **Implement error handling and retry logic** with exponential backoff for 429 rate limit responses.

- **Expand to additional qTest objects:** requirements, defects, and test case details for richer reporting.

---

*End of Knowledge Transfer Document*
