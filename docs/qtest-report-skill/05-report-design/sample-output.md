# Sample Report Output

This is the fully realized example of what `/qtest-report CL-416` produces. This serves as the **acceptance criteria** — when the real skill output matches this format and quality, it's done.

**Scenario:** Sprint 42 Regression Cycle with 61 runs, 5 failures, 2 blocked.

---

## What the user sees after running `/qtest-report CL-416`:

---

# Morning Test Execution Report

**Cycle:** Sprint 42 Regression Cycle (CL-416)
**Generated:** March 23, 2026 at 9:00 AM
**Pass Rate:** 84.9% (45/53 executed tests passed)

---

## Executive Summary

61 test runs across 3 suites.

- **45** passed
- **5** failed
- **2** blocked
- **1** incomplete
- **8** not yet executed

Overall health is moderate with an 84.9% pass rate. 5 failures need investigation — 3 are concentrated in TC-970 (Smoke Tests), suggesting a possible regression in that area. 2 tests are blocked on a payment infrastructure issue. 8 tests remain unexecuted.

---

## Status Breakdown

| Status | Count | Percentage |
|--------|------:|----------:|
| Passed | 45 | 73.8% |
| Failed | 5 | 8.2% |
| Blocked | 2 | 3.3% |
| Incomplete | 1 | 1.6% |
| Unexecuted | 8 | 13.1% |

---

## Suite-Level Results

| Suite | PID | Total | Passed | Failed | Blocked | Pass Rate |
|-------|-----|------:|-------:|-------:|--------:|----------:|
| Smoke Tests | TC-970 | 30 | 25 | 3 | 2 | 83.3% |
| Regression Suite | TC-498 | 23 | 20 | 2 | 0 | 87.0% |
| (direct under cycle) | — | 8 | 0 | 0 | 0 | N/A |

---

## Failure Analysis

### 1. Verify login with expired token (TR-1002)

| Field | Detail |
|-------|--------|
| **Suite** | Smoke Tests (TC-970) |
| **Status** | Failed |
| **Failed Step** | Step 3: Verify redirect to login page |
| **Expected** | HTTP 302 redirect to /login |
| **Actual** | HTTP 500 Internal Server Error |
| **Notes** | Server returned 500 instead of redirect on expired token. Backend is throwing an unhandled exception rather than gracefully redirecting. |
| **Executed** | March 22, 2026 at 6:45 PM |

---

### 2. Submit form with special characters (TR-1015)

| Field | Detail |
|-------|--------|
| **Suite** | Smoke Tests (TC-970) |
| **Status** | Failed |
| **Failed Step** | Step 5: Validate saved record |
| **Expected** | Full 500-character input preserved in database |
| **Actual** | Field value truncated at 255 characters |
| **Notes** | Database column appears to be VARCHAR(255) but the form allows 500-character input. Data loss on save. |
| **Executed** | March 22, 2026 at 6:47 PM |

---

### 3. Verify password reset email (TR-1018)

| Field | Detail |
|-------|--------|
| **Suite** | Smoke Tests (TC-970) |
| **Status** | Failed |
| **Failed Step** | Step 2: Verify email received |
| **Expected** | Password reset email arrives within 30 seconds |
| **Actual** | Email not received within 30-second timeout |
| **Notes** | SMTP service may be down in staging environment. Manual check shows no emails being sent. |
| **Executed** | March 22, 2026 at 6:50 PM |

---

### 4. Search results pagination (TR-1045)

| Field | Detail |
|-------|--------|
| **Suite** | Regression Suite (TC-498) |
| **Status** | Failed |
| **Failed Step** | Step 4: Verify page size |
| **Expected** | 25 results per page |
| **Actual** | 100 results returned (pagination parameter ignored) |
| **Notes** | The `pageSize` query parameter is not being respected by the search API. Default of 100 is always returned. |
| **Executed** | March 22, 2026 at 7:10 PM |

---

### 5. Export report to CSV (TR-1052)

| Field | Detail |
|-------|--------|
| **Suite** | Regression Suite (TC-498) |
| **Status** | Failed |
| **Failed Step** | Step 3: Download CSV file |
| **Expected** | CSV file downloads successfully (HTTP 200) |
| **Actual** | HTTP 403 Forbidden |
| **Notes** | User permissions may have changed. The test account previously had export permissions but now gets 403 on the download endpoint. |
| **Executed** | March 22, 2026 at 7:15 PM |

---

## Blocked Items

### Payment gateway integration (TR-1040)

- **Suite:** Regression Suite (TC-498)
- **Notes:** Staging payment API is down since March 20. Blocked pending infra fix — JIRA-4521
- **Since:** March 20, 2026

### Refund processing flow (TR-1041)

- **Suite:** Regression Suite (TC-498)
- **Notes:** Depends on payment gateway (TR-1040). Blocked until infra resolves JIRA-4521.
- **Since:** March 20, 2026

---

## Recommendations

- **TC-970 (Smoke Tests) needs immediate attention** — 3 of 5 failures are in this suite. This is the core smoke suite and a high concentration of failures here may indicate a broader regression.

- **Backend service issues detected** — TR-1002 (500 error on expired token) and TR-1018 (SMTP timeout) both point to backend/infrastructure problems. These are likely not test issues but environment issues. Recommend checking staging backend health.

- **Data integrity issue** — TR-1015 shows a VARCHAR(255) column accepting 500-character input at the form level. This is a real bug — data is being silently truncated. File a defect ticket.

- **Permission change** — TR-1052 (CSV export 403) suggests a recent permission change affecting the test account. Check with the admin team if export permissions were revoked.

- **Payment API blocked items are aging** — TR-1040 and TR-1041 have been blocked since March 20 (3 days). Check JIRA-4521 status and escalate if needed.

- **8 unexecuted tests** — All 8 are directly under the cycle (not in any suite). These should be prioritized for execution today.

---

*Report generated by `/qtest-report` skill | Data source: qTest Manager API v3*
