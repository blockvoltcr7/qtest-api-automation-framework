# Agent Interaction Patterns

How the agent should behave in every scenario — happy path, errors, edge cases, and follow-ups.

---

## Pattern 1: Happy Path

The standard successful flow.

```
User: /qtest-report CL-416

Agent: Generating morning report for CL-416...

[Agent runs: python pipeline/qtest_report_pipeline.py CL-416]
[Pipeline outputs JSON to stdout]
[Agent parses JSON, formats markdown]

Agent:
# Morning Test Execution Report
**Cycle:** Sprint 42 Regression Cycle (CL-416)
**Pass Rate:** 84.9%
...
[full formatted report]
```

**Key behaviors:**
- Show a brief "Generating..." message before running the pipeline
- Don't show raw JSON to the user — format it into the report template
- The pipeline progress messages (on stderr) can be shown as status updates

---

## Pattern 2: Missing Argument

User invokes without a cycle PID.

```
User: /qtest-report

Agent: Which test cycle should I generate a report for?

Provide the cycle PID (e.g., CL-416).

To see available cycles, I can run:
  python smoke_tests/02_test_get_cycles.py

User: CL-416

Agent: [proceeds with pipeline]
```

**Key behaviors:**
- Don't fail silently — ask for the required input
- Offer to help find available PIDs
- If `QTEST_DEFAULT_CYCLE_PID` is set in `.env` (future), use that as default

---

## Pattern 3: Authentication Error (401)

```
User: /qtest-report CL-416

Agent: [runs pipeline, gets exit code 1, stderr says "401 Unauthorized"]

Agent: The qTest API returned **401 Unauthorized**. Your Bearer token may be
expired or invalid.

**To fix:**
1. Log into qTest Site Administration
2. Go to **Download qTest Resources**
3. Generate a new API token
4. Update `QTEST_BEARER_TOKEN` in `smoke_tests/.env`
5. Try again: `/qtest-report CL-416`
```

---

## Pattern 4: PID Not Found (404)

```
User: /qtest-report CL-999

Agent: [runs pipeline, gets error: "Cycle PID 'CL-999' not found"]

Agent: Could not find test cycle **CL-999** in your qTest project
(Project ID: {id}).

This PID may not exist or may be in a different project. To see available
cycle PIDs, I can run:
  python smoke_tests/02_test_get_cycles.py

Would you like me to list available cycles?
```

---

## Pattern 5: Configuration Error

```
User: /qtest-report CL-416

Agent: [runs pipeline, gets config error]

Agent: The pipeline could not start due to a configuration error:
  - `QTEST_BEARER_TOKEN` is not set

**To fix:**
1. Navigate to `smoke_tests/`
2. Copy `.env.example` to `.env` if you haven't already
3. Fill in `QTEST_DOMAIN`, `QTEST_BEARER_TOKEN`, and `QTEST_PROJECT_ID`
4. Try again
```

---

## Pattern 6: Rate Limited (429)

```
User: /qtest-report CL-416

Agent: [runs pipeline, stderr shows "429 Rate Limited — retrying in 60s..."]

Agent: qTest rate-limited the API requests. The pipeline is retrying
automatically (waiting 60 seconds)...

[If retry succeeds: proceeds normally]
[If retry fails:]

Agent: Still rate-limited after retry. Try again in a few minutes, or
reduce the frequency of API calls.
```

---

## Pattern 7: No Failures (All Passing)

```
User: /qtest-report CL-420

Agent:
# Morning Test Execution Report
**Cycle:** Sprint 43 Smoke (CL-420)
**Pass Rate:** 100% (42/42 executed tests passed)

## Executive Summary
42 test runs across 2 suites. All executed tests passed.

## Status Breakdown
| Status | Count | Percentage |
|--------|------:|----------:|
| Passed | 42 | 100.0% |

## Failure Analysis
No failures detected — all executed tests passed.

## Recommendations
- All tests passing — cycle is green
- Consider adding new test cases if coverage feels thin
```

---

## Pattern 8: Partial Data Collection

Some suites succeed, some fail.

```
Agent:
# Morning Test Execution Report
**Cycle:** Sprint 42 Regression Cycle (CL-416)
**Pass Rate:** 84.9%

[... normal report sections ...]

## Data Collection Issues
- Could not fetch test runs for suite TC-498 (HTTP 429 — rate limited)
- Statistics are based on partial data (TC-970 and direct runs only)

**Recommendation:** Run the report again in a few minutes for complete data.
```

---

## Pattern 9: Large Cycle (500+ Runs)

```
User: /qtest-report CL-400

Agent: Generating morning report for CL-400... This cycle has many test
runs — data collection may take 30-60 seconds.

[pipeline runs with pagination across many pages]

Agent:
# Morning Test Execution Report
**Cycle:** Full Regression (CL-400)
**Pass Rate:** 91.2% (547/600 executed tests passed)
...
```

**Key behavior:** Warn the user about longer wait times for large cycles.

---

## Pattern 10: Network/VPN Error

```
User: /qtest-report CL-416

Agent: [runs pipeline, gets ConnectionError]

Agent: Cannot reach the qTest server at `{domain}.qtestnet.com`.

**Possible causes:**
- VPN is not connected (qTest may require VPN access)
- The `QTEST_DOMAIN` value in `.env` is incorrect
- qTest is experiencing an outage

**To diagnose:**
- Check your VPN connection
- Try: `ping {domain}.qtestnet.com`
- Verify `QTEST_DOMAIN` in `smoke_tests/.env`
```

---

## Pattern 11: Follow-Up Questions

After presenting the report, the agent retains the JSON data in context and can answer follow-ups.

### "Tell me more about a specific failure"

```
User: Tell me more about TR-1002

Agent: **TR-1002 — Verify login with expired token**

**Full details:**
- Suite: TC-970 (Smoke Tests)
- Status: Failed
- Failed at Step 3: "Verify redirect to login page"
  - Expected: HTTP 302 redirect to /login
  - Actual: HTTP 500 Internal Server Error
- Execution note: "Server returned 500 instead of redirect on expired token"
- Last executed: 2026-03-22 at 18:45 UTC

This suggests the backend's expired-token handling is broken — it's throwing
a 500 instead of gracefully redirecting. Likely a server-side bug, not a test issue.
```

### "Which suite is worst?"

```
User: Which suite has the worst pass rate?

Agent: **TC-970 (Smoke Tests)** has the worst pass rate at 83.3%:
- 30 runs: 25 passed, 3 failed, 2 blocked
- Contains 3 of the 5 total failures

TC-498 (Regression Suite) is at 87.0% with 2 failures.
```

### "Save this report"

```
User: Save this report to a file

Agent: [writes the markdown to reports/qtest-report-CL-416-2026-03-23.md]

Agent: Report saved to `reports/qtest-report-CL-416-2026-03-23.md`
```

### "Compare with last cycle" (Future capability)

```
User: How does this compare to CL-415?

Agent: I'd need to run the pipeline again for CL-415 to compare.
Would you like me to generate a report for CL-415 as well?

[This is a v2 feature — document as future capability]
```

---

## Agent Behavior Rules

1. **Always run the pipeline** — don't try to call the qTest API directly. The pipeline handles auth, pagination, error handling, and output formatting.

2. **Never show raw JSON** — always format it into the report template. The JSON is the internal contract, not the user-facing output.

3. **Retain JSON in context** — after formatting the report, keep the data available for follow-up questions.

4. **Be specific about errors** — don't just say "something went wrong." Map the error to a cause and a fix.

5. **Offer next steps** — after the report, suggest actions: "Want me to look into TR-1002?" or "Should I save this report?"

6. **Don't re-run the pipeline unnecessarily** — if the user asks a follow-up about the same cycle, answer from the JSON already in context.
