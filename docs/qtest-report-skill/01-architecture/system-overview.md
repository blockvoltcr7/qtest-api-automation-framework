# System Overview: `/qtest-report` Skill

## Problem Statement

Every morning, QA leads and engineers need to assess the state of test execution for active test cycles in qTest Manager. Today, this requires:

1. Logging into the qTest Manager web UI.
2. Navigating to the correct project and test cycle (e.g., "Sprint 42 Regression").
3. Manually expanding each test suite to review which test runs passed, failed, or remain unexecuted.
4. Clicking into individual failed runs to read failure notes and identify which test step broke.
5. Mentally (or in a spreadsheet) aggregating pass/fail/blocked counts across suites.
6. Copy-pasting findings into Slack or a standup doc.

This process takes 10-20 minutes per cycle, is error-prone, and produces inconsistent output depending on who runs it. The information exists in qTest's REST API, but nobody has built a reporting layer on top of it.

## Solution

A Claude Code slash command skill called `/qtest-report` that:

- Accepts a test cycle PID (e.g., `CL-416`) as input.
- Executes a Python pipeline that chains 5 qTest API calls to collect all test execution data.
- Analyzes failures by fetching the last-run test log for every failed test run, including step-level detail.
- Outputs structured JSON to stdout.
- Lets the Claude Code agent format the JSON into a clean, readable markdown report with summary stats, per-suite breakdowns, and failure analysis.

The entire flow runs locally in the terminal. No server, no CI pipeline, no browser.

## Components

The skill is composed of five components spanning three runtime boundaries (local filesystem, Claude Code agent, remote API).

### 1. Skill Definition File

**Path:** `.claude/commands/qtest-report.md`

This is the Claude Code skill instruction file. It contains:

- The prompt template that tells the agent what to do when the user invokes `/qtest-report`.
- Instructions for how to invoke the Python pipeline (via `Bash` tool).
- Rules for how to interpret the JSON output and format the markdown report.
- Guidance on error handling (missing cycle, auth failures, empty suites).

The agent reads this file at invocation time. It is not code; it is natural language instructions.

### 2. Python Pipeline Module

**Path:** `pipeline/qtest_report_pipeline.py`

This is a standalone Python script that:

- Accepts a `cycle_pid` argument on the command line.
- Imports `config.py` for authentication and session setup.
- Makes 5 sequential API calls to qTest Manager (see Data Flow doc for details).
- Performs client-side aggregation (counting statuses, computing pass rate).
- Fetches failure details (test logs with step-level data) for every failed run.
- Outputs a single JSON document to stdout.
- Outputs progress/debug messages to stderr (so they do not contaminate the JSON).

This module refactors and extends logic from the existing smoke test scripts (see below).

### 3. Shared Configuration Module

**Path:** `smoke_tests/config.py`

This existing module is reused directly by the pipeline. It provides:

- **`validate_config()`** -- Checks that required environment variables (`QTEST_DOMAIN` or `QTEST_BASE_URL`, auth credentials, `QTEST_PROJECT_ID`) are present. Exits with a clear error message if not.
- **`create_session()`** -- Creates a `requests.Session` pre-configured with auth headers. Supports both bearer token auth and username/password login (via `POST /oauth/token`).
- **`get_api_base()`** -- Returns the fully-qualified API v3 project base URL: `https://{domain}.qtestnet.com/api/v3/projects/{project_id}`.
- **`print_response_summary()`** -- Debug helper for printing API response details.

Authentication credentials are loaded from `smoke_tests/.env` via `python-dotenv`.

### 4. qTest Manager REST API v3

**External dependency.** The qTest Manager instance hosted at `https://{domain}.qtestnet.com`.

Endpoints used by the pipeline:

| # | Method | Endpoint | Purpose |
|---|--------|----------|---------|
| 1 | GET | `/api/v3/projects/{id}/test-cycles?expand=descendants` | Retrieve full cycle tree, resolve PID to numeric ID |
| 2 | GET | `/api/v3/projects/{id}/test-suites?parentId={cycleId}&parentType=test-cycle` | Get suites under cycle |
| 3 | GET | `/api/v3/projects/{id}/test-runs?parentId={suiteId}&parentType=test-suite&page={n}&pageSize=100` | Get runs per suite (paginated) |
| 4 | GET | `/api/v3/projects/{id}/test-runs/execution-statuses` | Get status ID-to-name mapping |
| 5 | GET | `/api/v3/projects/{id}/test-runs/{runId}/test-logs/last-run?expand=teststeplog.teststep` | Get failure details for failed runs |

All calls use bearer token authentication via the `Authorization` header.

### 5. Claude Code Agent

**Runtime:** The Claude Code CLI process running locally.

The agent is the orchestrator. Its responsibilities:

- Read the skill definition file when the user types `/qtest-report CL-416`.
- Invoke the Python pipeline via the `Bash` tool.
- Capture and parse the JSON output from stdout.
- Format a markdown report including: summary table, per-suite breakdown, failure details with step-level information.
- Present the report to the user in the terminal.
- Handle errors gracefully (explain what went wrong if the pipeline exits non-zero).

The agent does NOT call the qTest API directly. It delegates all API interaction to the Python pipeline.

## Deployment Model

This skill runs entirely locally. There is no deployment in the traditional sense.

- **No server.** The pipeline runs as a subprocess of the Claude Code CLI.
- **No CI/CD.** The skill is invoked on demand by the user typing `/qtest-report`.
- **No database.** All data is fetched live from qTest on every invocation.
- **No scheduled execution.** The user triggers the report when they need it.

**Prerequisites for use:**

1. Claude Code CLI installed and authenticated.
2. The `.claude/commands/qtest-report.md` skill file present in the repo.
3. Python 3.8+ with `requests` and `python-dotenv` installed.
4. A valid `smoke_tests/.env` file with qTest credentials and project ID.

## How It Fits With Existing Code

The pipeline module (`pipeline/qtest_report_pipeline.py`) is a refactored and extended version of logic already proven in the smoke test suite:

| Existing Smoke Test | What It Does | What Pipeline Reuses/Extends |
|---------------------|-------------|------------------------------|
| `smoke_tests/07_test_full_flow.py` | Resolves cycle PID, fetches suites, fetches runs, computes stats. Outputs a pretty-printed table and a JSON blob. | Pipeline reuses the same 4-call chain (`resolve_cycle_pid`, `get_test_suites`, `get_test_runs_paginated`, `get_execution_statuses`) and the `extract_status_from_run` logic. |
| `smoke_tests/06_test_get_logs.py` | Fetches the latest test log for a single run, including step-level details. | Pipeline adds a 5th API call: for every failed run, it calls `GET .../test-logs/last-run?expand=teststeplog.teststep` to get the failed step details. This logic comes from `06_test_get_logs.py`'s `get_latest_test_log` function. |
| `smoke_tests/config.py` | Auth, session creation, config validation. | Imported directly. No changes needed. |

The key extension over `07_test_full_flow.py` is the failure analysis step: instead of just counting how many runs failed, the pipeline fetches the *why* -- which step failed, what was expected, what actually happened, and any notes left by the executor.

## Key Architectural Principle

> **The pipeline outputs raw JSON to stdout. The agent handles markdown formatting.**

This separation is intentional and provides two important benefits:

### Testability

The Python pipeline can be tested independently of Claude Code:

```bash
# Run pipeline directly, inspect JSON output
python pipeline/qtest_report_pipeline.py CL-416 2>/dev/null | python -m json.tool

# Validate output schema
python pipeline/qtest_report_pipeline.py CL-416 2>/dev/null | python -c "
import sys, json
data = json.load(sys.stdin)
assert 'summary' in data
assert 'failures' in data
print('Schema OK')
"
```

You can write unit tests, integration tests, and regression tests against the pipeline without involving the agent at all.

### Flexibility

The report format can evolve without touching the Python code:

- Want a different markdown layout? Edit the skill definition file.
- Want to add a Slack summary? Have the agent produce a shorter version.
- Want CSV output? Tell the agent to reformat the JSON as CSV.
- Want to compare two cycles? Have the agent invoke the pipeline twice and diff the outputs.

The agent is the presentation layer. The pipeline is the data layer. They communicate via a well-defined JSON contract.

## Directory Structure

```
qTest API and Test Automation Framework Quality engineering/
+-- .claude/
|   +-- commands/
|       +-- qtest-report.md              # Skill definition (agent instructions)
+-- pipeline/
|   +-- qtest_report_pipeline.py         # Python pipeline module
+-- smoke_tests/
|   +-- .env                             # Credentials (not committed)
|   +-- .env.example                     # Template for credentials
|   +-- config.py                        # Shared auth/session config
|   +-- 01_test_auth.py                  # Auth smoke test
|   +-- 02_test_get_cycles.py            # Cycles smoke test
|   +-- 03_test_get_suites.py            # Suites smoke test
|   +-- 04_test_get_runs.py              # Runs smoke test
|   +-- 05_test_execution_statuses.py    # Status definitions smoke test
|   +-- 06_test_get_logs.py              # Test logs smoke test
|   +-- 07_test_full_flow.py             # Full flow smoke test
+-- docs/
    +-- qtest-report-skill/
        +-- 01-architecture/
            +-- system-overview.md       # This file
            +-- component-diagram.md     # Component and sequence diagrams
            +-- data-flow.md             # Data flow and transformations
```
