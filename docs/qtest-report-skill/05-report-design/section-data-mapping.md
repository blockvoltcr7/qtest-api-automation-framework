# Section-to-Data Mapping

Maps every report section to the exact JSON field(s) that populate it, with transformation rules.

---

## Visual Mapping

```
Pipeline JSON Output                          Report Sections
━━━━━━━━━━━━━━━━━━━                          ━━━━━━━━━━━━━━━

$.cycle_name ─────────────────────────────►   Header: Cycle name
$.cycle_pid ──────────────────────────────►   Header: Cycle PID
$.generated_at ───────────────────────────►   Header: Timestamp
$.summary.pass_rate ──────────────────────►   Header: Pass rate badge
$.summary.passed + $.summary.executed ────►   Header: "45/53 executed"

$.summary.total_runs ─────────────────────►   Executive Summary: total
len($.suites) ────────────────────────────►   Executive Summary: suite count
$.summary.{passed,failed,blocked,...} ────►   Executive Summary: bullet list
    (agent reasoning) ────────────────────►   Executive Summary: assessment

$.summary.* ──────────────────────────────►   Status Breakdown: table rows
    count / total_runs * 100 ─────────────►   Status Breakdown: percentages
$.summary.other_statuses ─────────────────►   Status Breakdown: extra rows

$.suites[] ───────────────────────────────►   Suite Results: table rows
    sort by pass_rate ASC ────────────────►   Suite Results: ordering

$.failures[] ─────────────────────────────►   Failure Analysis: entries
$.failures[n].failed_step ────────────────►   Failure Analysis: step details
$.failures[n].note ───────────────────────►   Failure Analysis: error notes

$.blocked_items[] ────────────────────────►   Blocked Items: entries

    (agent reasoning) ────────────────────►   Recommendations: content

$.data_collection_issues[] ───────────────►   Data Issues: bullet list
```

---

## Detailed Mapping Table

### Header Section

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Cycle name | `$.cycle_name` | Direct | Data |
| Cycle PID | `$.cycle_pid` | Direct | Data |
| Timestamp | `$.generated_at` | ISO 8601 → human-readable | Data |
| Pass rate | `$.summary.pass_rate` | Append "%" | Data |
| Passed/Executed | `$.summary.passed` / `$.summary.executed` | Format as "N/M" | Data |

### Executive Summary

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Total runs | `$.summary.total_runs` | Direct | Data |
| Suite count | `len($.suites)` | Computed | Computed |
| Passed count | `$.summary.passed` | Direct | Data |
| Failed count | `$.summary.failed` | Direct | Data |
| Blocked count | `$.summary.blocked` | Direct | Data |
| Incomplete count | `$.summary.incomplete` | Direct | Data |
| Unexecuted count | `$.summary.unexecuted` | Direct | Data |
| Assessment | — | Agent analyzes data holistically | Agent |

**Assessment generation rules:**
- If pass_rate >= 95%: "Cycle is in excellent health"
- If pass_rate >= 80%: "Overall health is good, {N} failures need investigation"
- If pass_rate >= 60%: "Significant failures detected — {N} tests need attention"
- If pass_rate < 60%: "Critical: majority of tests failing — immediate investigation required"
- Always mention if failures cluster in one suite
- Always mention unexecuted count if > 0

### Status Breakdown Table

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Status name | Hardcoded: Passed, Failed, Blocked, Incomplete, Unexecuted | — | Static |
| Count | `$.summary.{status}` | Direct | Data |
| Percentage | `count / $.summary.total_runs * 100` | Computed, 1 decimal place | Computed |
| Custom rows | `$.summary.other_statuses` keys/values | Add one row per custom status | Data |

### Suite-Level Results Table

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Suite name | `$.suites[n].name` | Direct | Data |
| Suite PID | `$.suites[n].pid` | Direct | Data |
| Total | `$.suites[n].total` | Direct | Data |
| Passed | `$.suites[n].passed` | Direct | Data |
| Failed | `$.suites[n].failed` | Direct | Data |
| Blocked | `$.suites[n].blocked` | Direct | Data |
| Pass Rate | `$.suites[n].pass_rate` | Append "%" | Data |

**Sort order:** Ascending by `pass_rate` — worst suite appears first to draw attention.

### Failure Analysis Entries

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Index | — | Sequential: 1, 2, 3... | Computed |
| Run name | `$.failures[n].run_name` | Direct | Data |
| Run PID | `$.failures[n].run_pid` | Direct | Data |
| Suite | `$.failures[n].suite_name` + `suite_pid` | Format as "Name (PID)" | Data |
| Status | `$.failures[n].status` | Direct (always "Failed") | Data |
| Failed step order | `$.failures[n].failed_step.order` | Prefix with "Step " | Data |
| Step description | `$.failures[n].failed_step.description` | Direct | Data |
| Expected | `$.failures[n].failed_step.expected` | Direct | Data |
| Actual | `$.failures[n].failed_step.actual` | Direct | Data |
| Notes | `$.failures[n].note` | Direct | Data |
| Executed at | `$.failures[n].executed_at` | ISO 8601 → readable | Data |

**Null handling:** If `failed_step` is null, replace the step fields with "No step-level details available."

### Blocked Items Entries

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Run name | `$.blocked_items[n].run_name` | Direct | Data |
| Run PID | `$.blocked_items[n].run_pid` | Direct | Data |
| Suite | `$.blocked_items[n].suite_name` + `suite_pid` | Format as "Name (PID)" | Data |
| Notes | `$.blocked_items[n].note` | Direct | Data |
| Since | `$.blocked_items[n].executed_at` | ISO 8601 → readable | Data |

### Recommendations Section

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| All content | — | Agent-generated analysis | Agent |

**What the agent looks for:**
1. **Failure clustering**: Group `$.failures[]` by `suite_pid`. If one suite has disproportionate failures, flag it.
2. **Error patterns**: Look for common strings in `$.failures[].note` or `$.failures[].failed_step.actual` (e.g., multiple "500" errors → backend issue).
3. **Unexecuted priority**: If `$.summary.unexecuted > 0`, recommend running them.
4. **Blocked item age**: If `executed_at` is more than 3 days old, flag as stale.
5. **Overall health**: Summarize whether the cycle is ready to ship or needs work.

### Data Collection Issues

| Report Field | JSON Path | Transform | Type |
|-------------|-----------|-----------|------|
| Issue list | `$.data_collection_issues[]` | Bulleted markdown list | Data |

**Conditional**: Only render this section if the array is non-empty.

---

## Transform Types

| Type | Meaning |
|------|---------|
| **Data** | Direct from JSON, possibly with simple formatting |
| **Computed** | Derived from JSON fields via arithmetic or counting |
| **Agent** | Generated by the agent's reasoning, not from JSON data |
| **Static** | Hardcoded labels or structure |
