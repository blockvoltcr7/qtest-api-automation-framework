# Error Handling

Complete error handling reference for the report skill pipeline. Covers HTTP errors, network failures, partial failures, retry policy, and timeout configuration.

---

## Error Matrix

| HTTP Status | Meaning | Pipeline Behavior | User-Facing Message |
|-------------|---------|-------------------|---------------------|
| `200` | Success | Continue to next step | -- |
| `401` | Unauthorized | **Abort immediately** | `Authentication failed -- check QTEST_BEARER_TOKEN in .env` |
| `403` | Forbidden | **Abort immediately** | `Insufficient permissions -- contact qTest admin` |
| `404` (on cycle resolve) | PID not found | **Abort** | `Cycle PID '{pid}' not found. Run 02_test_get_cycles.py to see available PIDs` |
| `404` (on test-log) | No execution log | **Skip gracefully** | *(none -- this is normal for unexecuted runs)* |
| `429` | Rate limited | **Wait and retry once**, then abort | `Rate limited by qTest. Retrying in {n} seconds...` |
| `500` | Internal server error | **Abort** | `qTest server error (500). Try again later.` |
| `502` | Bad gateway | **Abort** | `qTest server error (502). Try again later.` |
| `503` | Service unavailable | **Abort** | `qTest server error (503). Try again later.` |
| `504` | Gateway timeout | **Abort** | `qTest server error (504). Try again later.` |
| `ConnectionError` | Network / DNS / VPN | **Abort** | `Cannot reach qTest. Check VPN and QTEST_DOMAIN.` |
| `Timeout` | Request exceeded deadline | **Abort** | `Request to qTest timed out after 30 seconds. Check network or try again.` |

---

## Error Handling by Pipeline Stage

### Call 1 -- Resolve Cycle

| Scenario | Behavior |
|----------|----------|
| 200 but PID not found in tree | Abort. The API returned data, but the target PID does not exist in the cycle hierarchy. Message: `Cycle PID '{pid}' not found. Run 02_test_get_cycles.py to see available PIDs` |
| 401 / 403 | Abort. Authentication or permission issue detected on the first call. |
| Any other error | Abort. No data has been collected yet, so there is nothing partial to report. |

### Call 2 -- Get Suites

| Scenario | Behavior |
|----------|----------|
| 200 with empty array | Continue. The cycle has no suites. The pipeline still fetches runs directly under the cycle (Call 3 with `parentType=test-cycle`). |
| 404 | Abort. The cycle ID resolved in Call 1 does not exist (unlikely but possible if data changed between calls). |
| Any other error | Abort. |

### Call 3 -- Get Runs (per suite)

| Scenario | Behavior |
|----------|----------|
| 200 with empty array | Continue. The suite or cycle has no runs. Record zero runs for that container. |
| Error on one suite, others succeed | **Partial failure.** Include data from successful suites. Record the failed suite in a "Data Collection Issues" section of the report. |
| Error on the cycle-level run fetch | **Partial failure.** Include data from suites that succeeded. Note the issue. |
| All suite fetches fail | Abort. No meaningful data to report. |

### Call 4 -- Get Statuses

| Scenario | Behavior |
|----------|----------|
| 200 with empty array | Continue with an empty status map. Status names will fall back to the values already present in Call 3 results. |
| Any error | **Non-fatal.** The pipeline can still function using status names from the `properties` array in Call 3. Log a warning but continue. |

### Call 5 -- Get Failure Logs (per run)

| Scenario | Behavior |
|----------|----------|
| 404 | **Skip gracefully.** The run has no execution log. This is expected for runs that are marked as failed in metadata but have never actually been executed. |
| Error on some runs, others succeed | **Partial failure.** Include logs that were successfully fetched. Note which runs could not be retrieved in the "Data Collection Issues" section. |
| All log fetches fail | Continue. The report still includes the summary statistics from Call 3. The failure detail section will state that individual logs could not be retrieved. |

---

## Partial Failure Strategy

The pipeline is designed to produce the best report possible with the data it can collect. Complete abort only happens when the pipeline cannot collect **any** meaningful data.

### Rules

1. **Calls 1 and 2 are mandatory.** If either fails, the pipeline aborts because there is no structural data to build a report from.
2. **Call 3 supports partial success.** If some suites return runs and others error out, the report includes what is available and documents what is missing.
3. **Call 4 is best-effort.** The status map is a convenience. The pipeline can derive status names from the `properties` array in Call 3 responses.
4. **Call 5 is entirely best-effort.** Each failed log fetch is an independent skip. The report summary is unaffected.

### Data Collection Issues Section

When partial failures occur, the report includes a section at the bottom:

```
## Data Collection Issues

The following data could not be retrieved during report generation:

- Suite "Integration Tests" (TC-971): HTTP 500 when fetching test runs
- Test run TR-1045 "Verify checkout flow": HTTP 504 when fetching failure log
- Test run TR-1052 "Verify payment retry": Connection timeout when fetching failure log

These items are excluded from the statistics above. Re-run the report to attempt collection again.
```

---

## Retry Policy

| Condition | Retry? | Details |
|-----------|--------|---------|
| `429 Too Many Requests` | Yes, once | Wait for the number of seconds specified in the `Retry-After` response header. If no header is present, default to 10 seconds. After one retry, if the response is still 429, abort. |
| `5xx` server errors | No | Server errors are not retried. They indicate a qTest-side issue. |
| `401` / `403` | No | Authentication and permission errors will not resolve on retry. |
| `404` | No | Not found is a definitive response. |
| `ConnectionError` | No | Network issues require human intervention (VPN, DNS, etc.). |
| `Timeout` | No | A timeout suggests infrastructure stress. Retrying immediately would likely fail again. |

### Retry Implementation

```
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 10))
    log(f"Rate limited by qTest. Retrying in {retry_after} seconds...")
    sleep(retry_after)
    response = make_same_request()
    if response.status_code == 429:
        abort("Still rate limited after retry. Aborting pipeline.")
```

---

## Timeout Configuration

Each individual API call has a **30-second timeout**. This is defined as a configurable constant:

| Constant | Default Value | Unit | Description |
|----------|---------------|------|-------------|
| `API_TIMEOUT_SECONDS` | `30` | seconds | Maximum time to wait for a single HTTP response |

### Where to Configure

The timeout is set in the skill's configuration (typically in the environment or a constants module). To adjust:

```python
# In the skill configuration / constants
API_TIMEOUT_SECONDS = 30  # Increase for slow networks or large responses
```

### Timeout Behavior

- The timeout applies to each individual HTTP request, not to the pipeline as a whole.
- If a request times out, it is treated as a `Timeout` error (see error matrix above).
- Timed-out requests are **not retried** (only 429 responses trigger a retry).

---

## Error Response Format

qTest API error responses generally follow this structure:

```json
{
  "message": "Unauthorized",
  "status_code": 401
}
```

However, the format is not guaranteed to be consistent across all endpoints and error types. The skill extracts the `message` field if present, and falls back to the HTTP status code and reason phrase otherwise.

### Logging

All errors are logged with the following information:

| Field | Description |
|-------|-------------|
| Pipeline call number | Which of the 5 calls failed (e.g., "Call 3 - Get Runs") |
| HTTP method and URL | The full request URL (with sensitive tokens redacted) |
| HTTP status code | Numeric status code |
| Response body (truncated) | First 500 characters of the response body |
| Context | Parent container (e.g., "Suite TC-970" or "Run TR-1001") |

Tokens are **never** logged. The `Authorization` header is redacted to `Bearer ***` in all log output.

---

## Summary of Abort vs. Skip vs. Continue

| Behavior | When | Effect |
|----------|------|--------|
| **Abort** | Fatal errors on Calls 1-2; all Call 3 fetches fail; 401/403 on any call | Pipeline stops. No report is generated. Error message is returned to the user. |
| **Skip** | 404 on Call 5 (no log); individual Call 3 or Call 5 failures when others succeed | The specific item is excluded. The report is generated with available data and a "Data Collection Issues" note. |
| **Continue** | Call 4 failure; empty responses | Pipeline proceeds normally. Missing data is handled by fallbacks or noted as unavailable. |
