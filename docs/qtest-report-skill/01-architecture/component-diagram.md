# Component Diagrams: `/qtest-report` Skill

This document provides visual representations of the skill's architecture at multiple levels of detail: an ASCII flow diagram for quick reference, a Mermaid sequence diagram showing API-level interactions, and a Mermaid component diagram showing file-level dependencies.

---

## 1. ASCII Flow Diagram

This diagram shows the end-to-end flow from user invocation to report output.

```
    LOCAL MACHINE                                         NETWORK
    ============                                         =======

    User types "/qtest-report CL-416"
      |
      v
    +-----------------------------+
    | Claude Code CLI             |
    | (loads skill definition)    |
    +-----------------------------+
      |
      | reads .claude/commands/qtest-report.md
      v
    +-----------------------------+
    | Claude Code Agent           |
    | (interprets instructions)   |
    +-----------------------------+
      |
      | executes via Bash tool:
      | python pipeline/qtest_report_pipeline.py CL-416
      v
    +-----------------------------+
    | Python Pipeline             |
    | qtest_report_pipeline.py    |
    +-----------------------------+
      |
      | imports
      v
    +-----------------------------+
    | config.py                   |         +--------------------------+
    | - loads .env                |         |                          |
    | - validate_config()         |         |  qTest Manager REST API  |
    | - create_session()          |         |  (v3)                    |
    | - get_api_base()            |         |                          |
    +-----------------------------+         |  Endpoints:              |
      |                                     |  /test-cycles            |
      | authenticated session               |  /test-suites            |
      |                                     |  /test-runs              |
      v                                     |  /execution-statuses     |
    +-----------------------------+  HTTPS  |  /test-logs/last-run     |
    | API Call 1: GET test-cycles |-------->|                          |
    |   (resolve CL-416 -> ID)   |<--------|                          |
    +-----------------------------+         |                          |
      |                                     |                          |
    +-----------------------------+         |                          |
    | API Call 2: GET test-suites |-------->|                          |
    |   (suites under cycle)     |<--------|                          |
    +-----------------------------+         |                          |
      |                                     |                          |
    +-----------------------------+         |                          |
    | API Call 3: GET test-runs   |-------->|                          |
    |   (per suite, paginated)   |<--------|                          |
    +-----------------------------+         |                          |
      |                                     |                          |
    +-----------------------------+         |                          |
    | API Call 4: GET exec-status |-------->|                          |
    |   (status ID -> name map)  |<--------|                          |
    +-----------------------------+         |                          |
      |                                     |                          |
    +-----------------------------+         |                          |
    | API Call 5: GET test-logs   |-------->|                          |
    |   (per failed run only)    |<--------|                          |
    +-----------------------------+         +--------------------------+
      |
      | aggregation + JSON assembly
      v
    +-----------------------------+
    | JSON output to stdout       |
    | (progress to stderr)        |
    +-----------------------------+
      |
      | agent captures stdout
      v
    +-----------------------------+
    | Claude Code Agent           |
    | (parses JSON, formats MD)   |
    +-----------------------------+
      |
      v
    +-----------------------------+
    | Markdown report displayed   |
    | to user in terminal         |
    +-----------------------------+
```

### Boundary Summary

| Boundary | What Crosses It |
|----------|----------------|
| User -> Claude Code CLI | Slash command text: `/qtest-report CL-416` |
| CLI -> Agent | Skill definition file (`.claude/commands/qtest-report.md`) |
| Agent -> Python (Bash tool) | Shell command string; stdout/stderr streams back |
| Python -> config.py | Function imports (`create_session`, `get_api_base`, `validate_config`) |
| config.py -> .env file | Environment variable reads (filesystem I/O) |
| Python -> qTest API (NETWORK) | HTTPS requests with bearer token auth |
| Agent -> User | Formatted markdown text in terminal |

---

## 2. Mermaid Sequence Diagram

This diagram shows the temporal ordering of all interactions, including each individual API call.

```mermaid
sequenceDiagram
    actor User
    participant CLI as Claude Code CLI
    participant Skill as qtest-report.md<br/>(Skill File)
    participant Agent as Claude Code Agent
    participant Bash as Bash Tool
    participant Pipeline as qtest_report_pipeline.py
    participant Config as config.py
    participant Env as .env File
    participant API as qTest Manager API<br/>(v3)

    User->>CLI: /qtest-report CL-416
    CLI->>Skill: Read .claude/commands/qtest-report.md
    Skill-->>CLI: Skill instructions (markdown)
    CLI->>Agent: Initialize with skill instructions + user input

    Note over Agent: Agent interprets instructions,<br/>decides to run Python pipeline

    Agent->>Bash: python pipeline/qtest_report_pipeline.py CL-416

    Bash->>Pipeline: Execute with arg "CL-416"
    Pipeline->>Config: import (validate_config, create_session, get_api_base)
    Config->>Env: Load .env via python-dotenv
    Env-->>Config: QTEST_DOMAIN, QTEST_BEARER_TOKEN, QTEST_PROJECT_ID
    Config-->>Pipeline: Configuration validated

    Pipeline->>Config: create_session()
    Config-->>Pipeline: requests.Session with auth headers

    Pipeline->>Config: get_api_base()
    Config-->>Pipeline: "https://{domain}.qtestnet.com/api/v3/projects/{id}"

    Note over Pipeline,API: --- API Call 1: Resolve Cycle PID ---
    Pipeline->>API: GET /test-cycles?expand=descendants
    API-->>Pipeline: Full cycle tree (nested JSON)
    Note over Pipeline: Recursive search for pid=="CL-416"<br/>Extract: cycle_id, cycle_name

    Note over Pipeline,API: --- API Call 2: Get Test Suites ---
    Pipeline->>API: GET /test-suites?parentId={cycle_id}&parentType=test-cycle
    API-->>Pipeline: Array of suite objects
    Note over Pipeline: Extract: suite_id, suite_pid, suite_name per suite

    Note over Pipeline,API: --- API Call 3: Get Test Runs (per suite, paginated) ---
    loop For each suite
        loop For each page until empty
            Pipeline->>API: GET /test-runs?parentId={suite_id}&parentType=test-suite&page={n}&pageSize=100
            API-->>Pipeline: Array of run objects (up to 100)
        end
    end
    Note over Pipeline: Extract: run_id, run_pid, run_name, status per run

    Note over Pipeline,API: --- API Call 4: Get Execution Statuses ---
    Pipeline->>API: GET /test-runs/execution-statuses
    API-->>Pipeline: Array of status objects
    Note over Pipeline: Build map: {status_id: status_name}

    Note over Pipeline: --- Client-Side: Resolve Statuses & Aggregate ---
    Note over Pipeline: Count total/passed/failed/blocked/etc.<br/>Compute pass_rate. Identify failed runs.

    Note over Pipeline,API: --- API Call 5: Get Failure Details ---
    loop For each failed test run
        Pipeline->>API: GET /test-runs/{run_id}/test-logs/last-run?expand=teststeplog.teststep
        API-->>Pipeline: Test log with step details
    end
    Note over Pipeline: Extract: failed_step, note, timestamps per failure

    Note over Pipeline: --- Assemble Final JSON ---
    Pipeline-->>Bash: JSON to stdout (progress to stderr)
    Bash-->>Agent: Pipeline stdout + exit code

    Note over Agent: Agent parses JSON output,<br/>formats markdown report

    Agent-->>User: Markdown report displayed in terminal
```

### Reading the Sequence Diagram

- Solid arrows (`->>`) represent calls/requests.
- Dashed arrows (`-->>`) represent returns/responses.
- The `loop` boxes indicate repeated calls (pagination for runs, per-failure for logs).
- Everything above the `API` lifeline runs locally. Only the arrows crossing to `API` traverse the network.

---

## 3. Mermaid Component Diagram

This diagram shows the file-level architecture: which files exist, which modules import or invoke which other modules.

```mermaid
graph TB
    subgraph UserSpace["User's Terminal"]
        USER[User]
    end

    subgraph ClaudeCode["Claude Code Runtime (Local)"]
        CLI["Claude Code CLI"]
        AGENT["Claude Code Agent<br/>(LLM + Tool Use)"]
        BASH["Bash Tool<br/>(subprocess executor)"]
    end

    subgraph SkillDefinition[".claude/commands/"]
        SKILL_FILE["qtest-report.md<br/><i>Skill definition file</i><br/><i>Agent instructions + prompt template</i>"]
    end

    subgraph PipelineModule["pipeline/"]
        PIPELINE["qtest_report_pipeline.py<br/><i>Main pipeline script</i><br/><i>5 API calls + aggregation + JSON output</i>"]
    end

    subgraph SmokeTests["smoke_tests/"]
        CONFIG["config.py<br/><i>Auth, session factory,</i><br/><i>config validation, helpers</i>"]
        DOTENV[".env<br/><i>QTEST_DOMAIN</i><br/><i>QTEST_BEARER_TOKEN</i><br/><i>QTEST_PROJECT_ID</i>"]
        SMOKE_07["07_test_full_flow.py<br/><i>Original full flow test</i><br/><i>(pipeline is based on this)</i>"]
        SMOKE_06["06_test_get_logs.py<br/><i>Original test log fetcher</i><br/><i>(failure analysis based on this)</i>"]
    end

    subgraph ExternalAPI["qTest Manager (Remote)"]
        QTEST_API["REST API v3<br/>https://{domain}.qtestnet.com/api/v3"]
    end

    USER -- "/qtest-report CL-416" --> CLI
    CLI -- "reads" --> SKILL_FILE
    SKILL_FILE -- "instructions" --> AGENT
    AGENT -- "invokes" --> BASH
    BASH -- "executes" --> PIPELINE
    PIPELINE -- "imports" --> CONFIG
    CONFIG -- "loads" --> DOTENV
    PIPELINE -- "HTTPS requests" --> QTEST_API
    QTEST_API -- "JSON responses" --> PIPELINE
    PIPELINE -- "JSON to stdout" --> BASH
    BASH -- "stdout capture" --> AGENT
    AGENT -- "markdown report" --> USER

    SMOKE_07 -. "logic refactored into" .-> PIPELINE
    SMOKE_06 -. "failure analysis from" .-> PIPELINE
    SMOKE_07 -- "imports" --> CONFIG
    SMOKE_06 -- "imports" --> CONFIG

    style ExternalAPI fill:#ffe0e0,stroke:#cc0000
    style ClaudeCode fill:#e0e0ff,stroke:#0000cc
    style PipelineModule fill:#e0ffe0,stroke:#00cc00
    style SmokeTests fill:#fff0e0,stroke:#cc8800
    style SkillDefinition fill:#f0e0ff,stroke:#8800cc
```

### Component Roles

| Component | Type | Role |
|-----------|------|------|
| `qtest-report.md` | Skill definition | Natural language instructions telling the agent how to invoke the pipeline and format results |
| `qtest_report_pipeline.py` | Python script | Data layer -- makes all API calls, performs aggregation, outputs JSON |
| `config.py` | Python module | Infrastructure -- auth, session management, environment config |
| `.env` | Configuration file | Secrets storage -- credentials, domain, project ID |
| Claude Code Agent | LLM runtime | Orchestration + presentation -- invokes pipeline, formats report |
| qTest Manager API | External service | Data source -- all test execution data |
| `07_test_full_flow.py` | Smoke test | Ancestor -- pipeline refactors logic from this file |
| `06_test_get_logs.py` | Smoke test | Ancestor -- failure log fetching comes from this file |

### Dependency Direction

Dependencies flow downward and inward:

```
Agent --> Skill File (reads instructions)
Agent --> Pipeline (invokes via Bash)
Pipeline --> config.py (imports functions)
config.py --> .env (reads environment)
Pipeline --> qTest API (HTTPS calls)
```

No component has a reverse dependency. The pipeline does not know about the agent. `config.py` does not know about the pipeline. The API does not know about any of them. This makes each layer independently testable.

### Network Boundary

```
+-------------------------------------------------------+
|                    LOCAL MACHINE                        |
|                                                        |
|  User <-> CLI <-> Agent <-> Bash <-> Pipeline          |
|                                         |              |
|                                    config.py <-> .env  |
|                                         |              |
+--------- - - - - - - - - - - - - - - - | - - ---------+
                                          | HTTPS
                                          v
                              +---------------------+
                              | qTest Manager API   |
                              | (remote server)     |
                              +---------------------+
```

Only the Python pipeline crosses the network boundary. All other interactions are local: filesystem reads, subprocess execution, and stdout/stderr streaming.
