# Open Questions

Unresolved decisions that need input before or during implementation.

---

## Q1: Import Strategy

**Question:** How should `pipeline/qtest_report_pipeline.py` access functions from `smoke_tests/config.py`?

| Option | Approach | Pro | Con |
|--------|----------|-----|-----|
| **A** | Add `smoke_tests/` to `sys.path` | Simple, no duplication | Fragile path dependency |
| **B** | Extract shared code into `lib/qtest_client.py` | Clean architecture | Requires refactoring, more work |
| **C** | Copy needed functions into pipeline | Self-contained | Code duplication, two places to maintain |

**Recommended:** Option A for v1 (simplest path). Migrate to Option B when building the `QTestClient` class from the roadmap.

**Decision:** _Pending_

---

## Q2: Failure Log Fetch Limit

**Question:** Should we cap the number of failure logs fetched?

**Context:** If a cycle has 50 failures, that's 50 additional API calls to fetch test logs. This risks rate limiting (429) and slows down the pipeline.

| Option | Behavior |
|--------|----------|
| No cap | Fetch logs for all failed/blocked runs |
| Cap at 10 | Show 10 detailed + "Plus 40 more failures (details omitted)" |
| Cap at 20 | Show 20 detailed + count of remainder |

**Recommended:** Cap at 20. Show remaining as a summary count in the report. This balances detail with API politeness.

**Decision:** _Pending_

---

## Q3: Default Cycle PID

**Question:** Should users be able to set a default cycle PID in `.env`?

**Proposed:** Add `QTEST_DEFAULT_CYCLE_PID=CL-416` to `.env.example`. If set, `/qtest-report` without arguments uses this default instead of prompting.

**Recommended:** Yes — low effort, high convenience for daily use. The agent should still tell the user which cycle it's reporting on.

**Decision:** _Pending_

---

## Q4: Report Output Destination

**Question:** Should the report also be saved to a file automatically?

| Option | Behavior |
|--------|----------|
| Terminal only | Report displayed in Claude Code, not saved |
| Auto-save | Also write to `reports/qtest-report-{PID}-{date}.md` |
| On request | Only save when user asks "Save this report" |

**Recommended:** Terminal only for v1. Agent can save on request (Pattern in `agent-interaction-patterns.md`). Auto-save adds file management complexity.

**Decision:** _Pending_

---

## Q5: Blocked Items — Full Log Analysis?

**Question:** Should "Blocked" runs get the same log analysis as "Failed" runs?

**Context:** Blocked runs often have important notes about WHY they're blocked (e.g., "Payment API down — JIRA-4521"). Fetching their logs gives us this context.

**Recommended:** Yes — fetch logs for both Failed and Blocked. The notes field on blocked items is often the most actionable piece of information.

**Decision:** _Pending_

---

## Q6: Sub-Cycle Traversal

**Question:** Should the pipeline traverse nested sub-cycles?

**Example:** CL-416 contains sub-cycle CL-417, which contains suite TC-501. Currently, `07_test_full_flow.py` only gets suites **directly under CL-416**, missing TC-501.

**Context:** The `expand=descendants` response already contains the full tree. The data is available — we just need to recursively search for suites at all levels.

| Option | Behavior |
|--------|----------|
| Direct children only | Only suites under the target cycle (current behavior) |
| Full recursive | Traverse all sub-cycles and collect all suites |

**Recommended:** Full recursive for v1. The data is already fetched via `expand=descendants`, and users expect a cycle report to include everything under it.

**Decision:** _Pending_

---

## Q7: Progress Output

**Question:** How should the pipeline communicate progress while running?

**Context:** A cycle with 10 suites and 500 runs could take 30+ seconds. Users need feedback.

| Option | Mechanism |
|--------|-----------|
| Silent | JSON only on stdout, nothing on stderr |
| Stderr progress | `[1/5] Resolving cycle PID...` on stderr |
| JSON progress events | Structured progress on stderr |

**Recommended:** Simple stderr progress messages. The agent can optionally show these to the user. JSON goes exclusively to stdout.

```
[1/5] Resolving cycle PID 'CL-416'...
[2/5] Fetching test suites...
[3/5] Fetching test runs (3 suites, paginated)...
[4/5] Fetching execution statuses and failure logs (5 failures)...
[5/5] Computing statistics...
```

**Decision:** _Pending_

---

## Q8: Custom Status Names

**Question:** How should the pipeline handle custom execution statuses beyond the standard 5?

**Context:** Some qTest instances define custom statuses like "In Progress", "Not Applicable", "Deferred", etc. These won't match our hardcoded Passed/Failed/Blocked/Incomplete/Unexecuted categories.

**Recommended:** Handle dynamically:
- Standard statuses go in named fields (`summary.passed`, `.failed`, etc.)
- Any status not matching the standard 5 goes in `summary.other_statuses: {"Custom Name": count}`
- The report template includes extra rows for custom statuses
- No hardcoded status name matching — use the `execution-statuses` API as the source of truth

**Decision:** _Pending_

---

## Q9: Error Recovery Scope

**Question:** How aggressive should partial failure recovery be?

**Scenarios:**
1. Suite A returns data, Suite B returns 429 → Include A, note B in issues
2. Cycle resolves but test-suites call fails → Abort entirely?
3. Status API fails but runs succeed → Can we still show data without status names?

**Recommended:**
- If cycle resolution fails → abort (nothing else is possible)
- If suite/run fetching partially fails → include what we have, document issues
- If status API fails → use raw status IDs in the report instead of names
- If failure log fetching fails → show failure count without step details

**Decision:** _Pending_

---

## Q10: Pipeline as a Standalone Tool

**Question:** Should the pipeline be usable outside of Claude Code?

**Context:** The pipeline outputs clean JSON to stdout. This means it could be used in:
- CI/CD pipelines (GitHub Actions)
- Cron jobs that email morning reports
- Dashboards that consume the JSON
- Other AI agents or MCP servers

**Recommended:** Yes — design the pipeline to be a standalone CLI tool from the start. The skill file is just one consumer of the JSON output. This is already the case with our stdout/stderr separation design.

**Decision:** _Confirmed by design_ (stdout JSON + stderr progress already enables this)

---

## Summary

| # | Question | Recommended | Status |
|---|----------|-------------|--------|
| Q1 | Import strategy | Option A (sys.path) for v1 | Pending |
| Q2 | Failure log cap | 20 detailed, count rest | Pending |
| Q3 | Default cycle PID | Yes, via .env | Pending |
| Q4 | Report output destination | Terminal only for v1 | Pending |
| Q5 | Blocked log analysis | Yes, fetch for both | Pending |
| Q6 | Sub-cycle traversal | Full recursive | Pending |
| Q7 | Progress output | Stderr messages | Pending |
| Q8 | Custom statuses | Dynamic handling via other_statuses | Pending |
| Q9 | Error recovery scope | Partial recovery where possible | Pending |
| Q10 | Standalone pipeline | Yes (already by design) | Confirmed |
