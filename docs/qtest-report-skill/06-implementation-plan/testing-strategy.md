# Testing Strategy

How to validate each component and the skill end-to-end.

---

## Testing Levels

```
Level 4: Edge Case Testing
    ▲
Level 3: Skill Testing (end-to-end with Claude Code)
    ▲
Level 2: Integration Testing (pipeline against live qTest)
    ▲
Level 1: Unit Testing (pipeline functions with mocked API)
```

---

## Level 1: Unit Testing

**Goal:** Test each pipeline function in isolation with mocked API responses.

**Framework:** `pytest` with `unittest.mock.patch` (or `responses` library for HTTP mocking)

**Test fixtures:** Use sample JSON from `smoke_tests/DEVELOPER_GUIDE.md` Section 6.

### Test Cases

#### `resolve_cycle_pid()`

| Test | Input | Expected |
|------|-------|----------|
| Find root cycle | Tree with CL-416 at root | Returns cycle object with id=67890 |
| Find nested cycle | Tree with CL-417 inside CL-416 | Returns CL-417 object |
| PID not found | Tree without CL-999 | Returns None |
| Empty tree | `[]` | Returns None |

#### `get_test_suites()`

| Test | Input | Expected |
|------|-------|----------|
| Normal response | 2-suite JSON array | Returns list of 2 suite dicts |
| Empty suites | `[]` | Returns empty list |

#### `get_test_runs_paginated()`

| Test | Input | Expected |
|------|-------|----------|
| Single page (50 runs) | Mock: page 1 returns 50 items | Returns 50 runs |
| Multi-page (150 runs) | Mock: page 1 returns 100, page 2 returns 50 | Returns 150 runs |
| Empty | Mock: page 1 returns `[]` | Returns empty list |
| Exact page boundary (100) | Mock: page 1 returns 100, page 2 returns `[]` | Returns 100 runs |

#### `extract_status_from_run()`

| Test | Input | Expected |
|------|-------|----------|
| Status in properties | Run with `properties[field_name=Status].field_value_name="Passed"` | Returns "Passed" |
| Status in latest_test_log | Run with `latest_test_log.status.name="Failed"` | Returns "Failed" |
| Status in exe_status | Run with `exe_status: 601`, status_map `{601: "Passed"}` | Returns "Passed" |
| No status found | Run with empty properties | Returns "Unknown" |

#### `get_failure_details()`

| Test | Input | Expected |
|------|-------|----------|
| Failed with step logs | Mock log with 3 steps, step 2 failed | `failed_step.order == 2` |
| All steps passed but run failed | Mock log where all steps "Passed" | `failed_step is None` |
| 404 (no log) | Mock 404 response | Returns None |
| No step logs in response | Mock log with empty `test_step_logs` | `failed_step is None` |

#### Aggregation

| Test | Input | Expected |
|------|-------|----------|
| Normal counts | 10 Passed, 3 Failed, 2 Blocked | `pass_rate = 66.7` (10/15 * 100) |
| All passing | 20 Passed, 0 Failed | `pass_rate = 100.0` |
| All unexecuted | 0 Passed, 10 Unexecuted | `pass_rate = 0` (0 executed) |
| Custom statuses | 5 Passed, 2 "In Progress" | `other_statuses = {"In Progress": 2}` |

---

## Level 2: Integration Testing

**Goal:** Run the full pipeline against a live qTest instance.

**Prerequisites:** Valid `.env` with real credentials and a known cycle PID.

### Run the pipeline

```bash
cd "/path/to/repo"
python pipeline/qtest_report_pipeline.py CL-416
```

### Validation checklist

- [ ] Exit code is 0
- [ ] stdout contains valid JSON (parseable by `python -m json.tool`)
- [ ] JSON has all required top-level keys: `cycle_pid`, `cycle_name`, `cycle_id`, `generated_at`, `summary`, `suites`, `failures`, `blocked_items`, `data_collection_issues`
- [ ] `summary.total_runs` > 0
- [ ] `summary.pass_rate` is between 0 and 100
- [ ] `summary.executed` == `total_runs - unexecuted`
- [ ] `summary.passed + failed + blocked + incomplete + unexecuted` == `total_runs`
- [ ] Each suite in `suites[]` has `pid`, `name`, `total`, `pass_rate`
- [ ] Sum of all `suites[].total` ≈ `summary.total_runs` (may differ if direct-cycle runs exist)
- [ ] If failures exist, each has `run_pid`, `run_name`, `suite_pid`, `status`, `note`
- [ ] If failures have `failed_step`, it has `order`, `description`, `expected`, `actual`

### Cross-validate with existing scripts

```bash
# Run the old full flow script and compare counts
python smoke_tests/07_test_full_flow.py CL-416

# The total_runs and per-status counts should match
```

---

## Level 3: Skill Testing

**Goal:** Test the full end-to-end flow through Claude Code.

### Test procedure

1. Open Claude Code in the repo directory
2. Type `/qtest-report CL-416`
3. Observe the agent's behavior

### Validation checklist

- [ ] Agent runs the pipeline without manual intervention
- [ ] No raw JSON shown to user (only formatted report)
- [ ] Report contains all sections:
  - [ ] Header with cycle name, PID, pass rate
  - [ ] Executive Summary with counts
  - [ ] Status Breakdown table
  - [ ] Suite-Level Results table
  - [ ] Failure Analysis (if failures exist)
  - [ ] Blocked Items (if blocked exist)
  - [ ] Recommendations
- [ ] Failure details include step-level information
- [ ] Report structure matches `05-report-design/sample-output.md`
- [ ] Agent can answer follow-up questions about the data

### Follow-up tests

After the report is displayed:
- Ask: "Tell me more about TR-1002" → Agent should show detailed failure info
- Ask: "Which suite is worst?" → Agent should identify by pass rate
- Ask: "Save this report" → Agent should write markdown to a file

---

## Level 4: Edge Case Testing

| # | Test Case | Input | Expected Behavior | How to Test |
|---|-----------|-------|-------------------|-------------|
| 1 | Invalid PID | `CL-999` | Error: "PID not found" with available PIDs | Run pipeline with non-existent PID |
| 2 | No argument | `/qtest-report` | Agent asks for PID | Invoke skill without args |
| 3 | Empty cycle | Cycle with 0 suites, 0 runs | Report says "No test suites found" | Find/create an empty cycle |
| 4 | All passing | Cycle with 0 failures | Failure Analysis says "No failures detected" | Use a fully-passing cycle |
| 5 | Large cycle | 500+ test runs | Pagination works, complete report | Use a large cycle |
| 6 | Expired token | Bad QTEST_BEARER_TOKEN | Error: "401 Unauthorized" with fix instructions | Set an invalid token |
| 7 | Missing .env | No .env file | Error: "CONFIGURATION ERROR" | Rename .env temporarily |
| 8 | Network error | VPN disconnected | Error: "Cannot reach qTest" | Disconnect VPN |
| 9 | Rate limited | Rapid successive calls | 429 retry, then abort or succeed | Run multiple times quickly |
| 10 | Custom statuses | qTest instance with custom statuses | Statuses appear in report | Use instance with custom statuses |
| 11 | No step logs | Failed run without step details | "No step details available" | Test against run with no steps |
| 12 | Partial failure | One suite errors, others succeed | Report with partial data + Data Collection Issues | Mock network failure mid-pipeline |

---

## Regression Check

After all testing, verify existing functionality is unaffected:

```bash
cd smoke_tests/

# All existing scripts should still work
python 01_test_auth.py
python 02_test_get_cycles.py
python 05_test_execution_statuses.py
python 07_test_full_flow.py CL-416
```

No existing files are modified — the pipeline is entirely additive. But verify imports and paths haven't been accidentally changed.
