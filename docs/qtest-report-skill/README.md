# `/qtest-report` Skill — Planning Documentation

## Why This Exists

Every morning, the QE team spends 15+ minutes manually navigating qTest Manager to check smoke test results:

1. Open qTest, navigate to Test Execution
2. Find the test cycle (e.g., CL-416)
3. Drill into each test suite
4. Identify which tests failed
5. Click into each failure to understand **why** it failed
6. Write up a summary report for the team

This is repetitive, manual, and error-prone. The `/qtest-report` skill automates this entire workflow — an agent calls the qTest API, aggregates the data, analyzes failures, and produces a structured morning report in seconds.

---

## What the Skill Does

Given a test cycle PID (e.g., `CL-416`), the agent:

1. **Resolves** the PID to a numeric ID via the qTest API
2. **Retrieves** all test suites and test runs under the cycle
3. **Maps** execution statuses (Passed, Failed, Blocked, etc.)
4. **Fetches failure details** — which step failed, error notes, timestamps
5. **Produces** a structured markdown morning report with executive summary, status breakdown, per-suite results, and failure analysis

---

## Documentation Map

| Folder | Contents | Start Here If... |
|--------|----------|-------------------|
| [`01-architecture/`](01-architecture/) | System overview, component diagrams, data flow | You want the big picture |
| [`02-api-reference/`](02-api-reference/) | Endpoint catalog, response schemas, error handling | You want API details |
| [`03-pipeline/`](03-pipeline/) | 5-phase pipeline breakdown with inputs/outputs per phase | You want to understand the execution flow |
| [`04-skill-design/`](04-skill-design/) | Skill file spec, I/O contract, agent behavior patterns | You want to understand how the Claude Code skill works |
| [`05-report-design/`](05-report-design/) | Report template, data mappings, sample output | You want to see what the final report looks like |
| [`06-implementation-plan/`](06-implementation-plan/) | Build order, testing strategy, open questions | You want to know how we'll build it |

---

## Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Pipeline outputs JSON; agent formats the report** | Keeps the Python pipeline independently testable. Report format can evolve without changing Python code. |
| 2 | **Reuse existing `config.py` and smoke test logic** | Auth, session management, PID resolution, pagination, and status extraction are already written and tested in `smoke_tests/`. No need to rebuild. |
| 3 | **Failure log fetching is the key new capability** | The existing `07_test_full_flow.py` computes pass/fail counts but never fetches individual test logs. The skill adds targeted log retrieval for failed/blocked runs to answer "why did it fail?" |
| 4 | **Skill file = agent instructions, not executable code** | `.claude/commands/qtest-report.md` tells the agent what to do step-by-step. The agent uses Bash to run the Python pipeline and then formats the output. |
| 5 | **Fetch logs only for failed/blocked runs** | Avoids unnecessary API calls. A cycle with 60 runs but only 5 failures makes 5 log calls, not 60. |

---

## Existing Code We Build On

| File | What We Reuse |
|------|---------------|
| `smoke_tests/config.py` | `create_session()`, `get_api_base()`, `validate_config()` — auth and configuration |
| `smoke_tests/07_test_full_flow.py` | `resolve_cycle_pid()`, `get_test_runs_paginated()`, `extract_status_from_run()`, `Counter`-based aggregation |
| `smoke_tests/06_test_get_logs.py` | `get_latest_test_log()` with `expand=teststeplog.teststep` for step-level failure details |
| `smoke_tests/DEVELOPER_GUIDE.md` | Complete request/response JSON schemas |
| `qtest-api-test-execution-research.md` | API endpoint reference and call flow documentation |

---

## Status

| Document | Status |
|----------|--------|
| 01-architecture/ | Draft |
| 02-api-reference/ | Draft |
| 03-pipeline/ | Draft |
| 04-skill-design/ | Draft |
| 05-report-design/ | Draft |
| 06-implementation-plan/ | Draft |
