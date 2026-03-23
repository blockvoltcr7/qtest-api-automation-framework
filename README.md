# qTest API Automation Framework

A Python-based toolkit for interfacing with the **Tricentis qTest Manager REST API (v3)** to retrieve test execution data — test cycles, test suites, test runs, and execution statistics. Designed as the foundation for building AI agent skills that can query qTest from tools like GitHub Copilot CLI.

---

## The Problem

qTest Manager stores rich test execution data — cycles, suites, runs, pass/fail results — but there's no built-in API endpoint that gives you aggregated statistics. If you want to answer a question like *"What's the pass rate for test cycle CL-416?"*, you have to chain together multiple API calls and compute the stats yourself.

This project solves that by providing ready-to-run Python scripts that handle the full workflow: PID resolution, hierarchical traversal, pagination, and client-side aggregation.

## What This Does

Given a **Test Cycle PID** like `CL-416`, the framework:

1. Resolves the human-readable PID to a numeric internal ID
2. Retrieves all **Test Suites** nested under that cycle (e.g. `TC-970`, `TC-498`)
3. Fetches all **Test Runs** within each suite (with pagination)
4. Maps execution statuses using the project's status definitions
5. Computes and outputs statistics — both as a formatted table and as JSON

```
┌─────────────────────────────────────────────────┐
│  OVERALL STATISTICS for CL-416                  │
├──────────────────────┬──────────┬───────────────┤
│  Status              │  Count   │  Percentage   │
├──────────────────────┼──────────┼───────────────┤
│  Passed              │  45      │   73.8%       │
│  Failed              │  5       │    8.2%       │
│  Blocked             │  2       │    3.3%       │
│  Incomplete          │  1       │    1.6%       │
│  Unexecuted          │  8       │   13.1%       │
└──────────────────────┴──────────┴───────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.8+
- A qTest Manager account with **Premium** or **Elite** plan (required for API v3)
- A Bearer token from qTest Site Administration

### Setup

```bash
# Clone the repo
git clone https://github.com/blockvoltcr7/qtest-api-automation-framework.git
cd qtest-api-automation-framework/smoke_tests

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure your credentials
cp .env.example .env
# Edit .env with your domain, Bearer token, and Project ID
```

### Configure `.env`

```env
QTEST_DOMAIN=your-domain                    # e.g. "mycompany" for mycompany.qtestnet.com
QTEST_BEARER_TOKEN=your-bearer-token-here   # from qTest Site Admin → Download qTest Resources
QTEST_PROJECT_ID=12345                      # numeric ID from qTest URL
```

### Run

```bash
# Verify authentication
python 01_test_auth.py

# Full end-to-end: get stats for a test cycle
python 07_test_full_flow.py CL-416
```

---

## Smoke Test Scripts

Each script targets a single API capability and can be run independently. They're numbered in the order you'd typically run them:

| Script | What It Tests | Command |
|--------|--------------|---------|
| `01_test_auth.py` | Token validation, list projects | `python 01_test_auth.py` |
| `02_test_get_cycles.py` | Fetch test cycles, PID → ID resolution | `python 02_test_get_cycles.py CL-416` |
| `03_test_get_suites.py` | Get test suites under a cycle | `python 03_test_get_suites.py CL-416` |
| `04_test_get_runs.py` | Get test runs under a suite or cycle | `python 04_test_get_runs.py TC-970` |
| `05_test_execution_statuses.py` | Retrieve status definitions | `python 05_test_execution_statuses.py` |
| `06_test_get_logs.py` | Get test logs / execution results | `python 06_test_get_logs.py 12345` |
| `07_test_full_flow.py` | **End-to-end:** cycle → suites → runs → stats | `python 07_test_full_flow.py CL-416` |

Every script outputs `[PASS]`, `[FAIL]`, or `[WARN]` indicators along with the raw JSON responses so you can inspect the actual API response schemas.

---

## Project Structure

```
├── smoke_tests/
│   ├── .env.example                  # Configuration template
│   ├── requirements.txt              # Python dependencies
│   ├── config.py                     # Shared: env loader, session factory, auth, helpers
│   ├── 01_test_auth.py               # Authentication smoke test
│   ├── 02_test_get_cycles.py         # Test cycles + PID resolution
│   ├── 03_test_get_suites.py         # Test suites under a cycle
│   ├── 04_test_get_runs.py           # Test runs under a suite/cycle
│   ├── 05_test_execution_statuses.py # Execution status definitions
│   ├── 06_test_get_logs.py           # Test logs (latest + history)
│   ├── 07_test_full_flow.py          # Full end-to-end flow with stats
│   └── DEVELOPER_GUIDE.md           # Detailed guide with request/response schemas
├── qtest-api-test-execution-research.md  # API research & endpoint reference
├── qTest_API_Knowledge_Transfer.docx     # Team KT document
├── .gitignore
└── README.md
```

---

## API Endpoints Used

All calls target `https://{domain}.qtestnet.com/api/v3/projects/{projectId}/...`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/test-cycles?expand=descendants` | Fetch cycles with full hierarchy |
| `GET` | `/test-suites?parentId={id}&parentType=test-cycle` | Suites under a cycle |
| `GET` | `/test-runs?parentId={id}&parentType=test-suite` | Runs under a suite |
| `GET` | `/test-runs/execution-statuses` | Status definitions (Passed, Failed, etc.) |
| `GET` | `/test-runs/{id}/test-logs/last-run` | Latest execution result for a run |
| `GET` | `/test-runs/{id}/test-logs` | Full execution history |

For complete request/response schemas with sample JSON, see [`smoke_tests/DEVELOPER_GUIDE.md`](smoke_tests/DEVELOPER_GUIDE.md).

---

## qTest Identifier Reference

qTest uses human-readable PIDs alongside numeric internal IDs. The API requires numeric IDs, but all responses include both.

| Prefix | Object Type | Example | How to Resolve |
|--------|-------------|---------|----------------|
| `CL-` | Test Cycle | `CL-416` | Fetch all cycles, filter by `pid` field |
| `TC-` | Test Suite | `TC-970` | Found in cycle descendants or suite listings |
| `TR-` | Test Run | `TR-1234` | Found in run listings under suites/cycles |
| `TS-` | Test Case | `TS-5678` | Linked from test runs via `test_case` field |

---

## Authentication

The framework supports two authentication methods:

**Bearer Token (recommended)** — A pre-generated API token from qTest Site Administration under "Download qTest Resources." Set `QTEST_BEARER_TOKEN` in your `.env`. This token does not expire unless explicitly revoked.

**Username/Password** — The `POST /oauth/token` login flow. Set `QTEST_USERNAME` and `QTEST_PASSWORD` in your `.env`. The framework handles the token exchange automatically.

---

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **`requests` library** (not httpx, not urllib3) | Industry standard, synchronous workflow doesn't need async, team familiarity |
| **No qTest SDK** | Direct API control, fewer dependencies, easier adaptation to agent skills |
| **`python-dotenv` for config** | Simple `.env` file approach; no secrets in code |
| **Client-side statistics** | qTest has no stats endpoint; aggregation is done in Python |
| **Pagination in full flow** | API defaults to 100 results/page; script 07 loops all pages automatically |

---

## Known Limitations

- **No direct PID lookup** — The qTest API has no endpoint to fetch a cycle by PID. You must retrieve all cycles and filter client-side. The `expand=descendants` parameter helps by returning the full tree in one call.
- **Rate limiting** — qTest returns `429 Too Many Requests` if you call too frequently. No retry logic is implemented yet in the smoke tests.
- **Status field location varies** — Depending on qTest version, test run status may appear in different places within the `properties` array. The scripts handle multiple formats but your instance may differ.
- **Pagination on individual scripts** — Only `07_test_full_flow.py` handles multi-page results. Scripts 02–06 show page 1 only.

---

## Documentation

| Document | Description |
|----------|-------------|
| [`DEVELOPER_GUIDE.md`](smoke_tests/DEVELOPER_GUIDE.md) | Script-by-script guide, sample request/response JSON schemas, output interpretation, troubleshooting |
| [`qtest-api-test-execution-research.md`](qtest-api-test-execution-research.md) | Full API research — every endpoint, parameters, call flow diagram, identifier cheat sheet |
| [`qTest_API_Knowledge_Transfer.docx`](qTest_API_Knowledge_Transfer.docx) | Word document for team distribution — architecture, setup, flow, next steps |

---

## Roadmap

- [ ] Validate smoke tests against live qTest instance
- [ ] Refactor into a reusable `QTestClient` class with retry logic and caching
- [ ] Build an MCP (Model Context Protocol) server for AI agent integration
- [ ] Create GitHub Copilot CLI agent skill for natural language qTest queries
- [ ] Add interactive HTML dashboard for test cycle statistics
- [ ] Expand to requirements, defects, and test case management APIs
- [ ] Add CI/CD pipeline (GitHub Actions) for automated smoke test validation

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## License

This project is for internal use by the Quality Engineering team. Contact the repository owner for usage permissions.
