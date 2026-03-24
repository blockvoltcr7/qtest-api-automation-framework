# Skill File Specification: `/qtest-report`

## File Location

The skill file lives at:

```
.claude/commands/qtest-report.md
```

Claude Code discovers slash commands by scanning the `.claude/commands/` directory for `.md` files. The filename (minus the `.md` extension) becomes the command name. In this case, `qtest-report.md` registers the command `/qtest-report`.

This convention means:
- No registration step is needed. Drop the file in the directory and the command is available.
- The file must have a `.md` extension. Claude Code ignores other file types in this directory.
- Subdirectories are not scanned. All skill files must be directly inside `.claude/commands/`.
- The project can have multiple skill files (e.g., `qtest-report.md`, `qtest-setup.md`, `qtest-debug.md`).

## How Claude Code Loads the Skill

When a user types `/qtest-report CL-416` in the Claude Code CLI:

1. Claude Code reads `.claude/commands/qtest-report.md` from disk.
2. It replaces every occurrence of `$ARGUMENTS` in the file with the user-provided string (`CL-416`).
3. The resulting text is presented to the agent as instructions (effectively a system prompt for this turn).
4. The agent follows the instructions, using its available tools (Bash, Read, Write, etc.) to complete the task.

If the user types `/qtest-report` with no arguments, `$ARGUMENTS` is replaced with an empty string. The skill file must handle this case explicitly (see the instructions below).

## File Structure

The skill file is a plain markdown document. It is not code — it is natural language instructions that the agent interprets. The structure follows a pattern:

| Section | Purpose |
|---------|---------|
| Title + summary | One-line description of what the skill does |
| Arguments | Documents what `$ARGUMENTS` contains |
| Instructions | Step-by-step procedure the agent follows |
| Report Template | The exact markdown template the agent uses for output |
| Follow-up Capabilities | What the agent can do after presenting the report |
| Error Handling | How the agent should respond to specific failure modes |

## Draft Skill File Content

Below is the complete content outline for `.claude/commands/qtest-report.md`. This is what the agent will receive as instructions when the user invokes the skill.

```markdown
# qTest Morning Report Generator

Generate a structured morning test execution report for a qTest test cycle.

## Arguments

- `$ARGUMENTS` — The test cycle PID (e.g., "CL-416")

## Instructions

1. **Validate input.** If `$ARGUMENTS` is empty or missing, ask the user which test cycle
   to report on. Suggest they run `python smoke_tests/02_test_get_cycles.py` to see
   available cycle PIDs. Wait for their response before proceeding.

2. **Run the pipeline script.** Execute the following command using the Bash tool:
   ```
   cd smoke_tests && python ../pipeline/qtest_report_pipeline.py $ARGUMENTS
   ```
   Capture both stdout and stderr. The script outputs JSON to stdout on success.

3. **Handle errors.** If the script exits with a non-zero exit code:
   - If stderr contains "401" or "Unauthorized": tell the user their Bearer token is
     expired and walk them through regenerating it in qTest Site Admin. The token goes
     in `smoke_tests/.env` as `QTEST_BEARER_TOKEN`.
   - If stderr contains "not found" or "404": tell the user the cycle PID was not found.
     Suggest they check the PID and list available cycles.
   - If stderr contains "429" or "rate limit": tell the user to wait 60 seconds and retry.
   - For any other error: show the full stderr output and suggest checking network
     connectivity and `.env` configuration.
   Do not proceed to report formatting if the pipeline failed entirely.

4. **Parse the JSON output.** The pipeline writes a single JSON object to stdout.
   Parse it to extract: cycle metadata, summary stats, per-suite breakdowns, failure
   details, blocked items, and any data collection issues.

5. **Format the report.** Use the Report Template below. Fill in every placeholder with
   data from the parsed JSON. Follow these formatting rules:
   - Use exact field values from the JSON; do not round or estimate.
   - For pass_rate, display as a percentage with one decimal place (e.g., "75.0%").
   - In the Suite Breakdown table, sort suites by pass_rate ascending (worst first).
   - In the Failure Analysis section, include the failed step detail if available.
   - If there are no failures, say "No failures detected" in the Failure Analysis section.
   - If there are no blocked items, omit the Blocked Items section entirely.
   - If data_collection_issues is non-empty, include a Data Quality Notes section.

6. **Present the report.** Display the formatted markdown report in the terminal.

## Report Template

```
# Test Execution Report: {cycle_name}

**Cycle:** {cycle_pid} | **Generated:** {generated_at} | **Project:** qTest Manager

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total Runs | {summary.total_runs} |
| Executed | {summary.executed} |
| Passed | {summary.passed} |
| Failed | {summary.failed} |
| Blocked | {summary.blocked} |
| Incomplete | {summary.incomplete} |
| Unexecuted | {summary.unexecuted} |
| **Pass Rate** | **{summary.pass_rate}%** |

---

## Suite Breakdown

| Suite | Total | Passed | Failed | Blocked | Unexecuted | Pass Rate |
|-------|-------|--------|--------|---------|------------|-----------|
| {suite.name} ({suite.pid}) | {suite.total} | {suite.passed} | {suite.failed} | {suite.blocked} | {suite.unexecuted} | {suite.pass_rate}% |

---

## Failure Analysis

### {failure.run_name} ({failure.run_pid})
- **Suite:** {failure.suite_name} ({failure.suite_pid})
- **Status:** {failure.status}
- **Executed:** {failure.executed_at}
- **Failed Step:** Step {failure.failed_step.order} — {failure.failed_step.description}
  - Expected: {failure.failed_step.expected}
  - Actual: {failure.failed_step.actual}
- **Note:** {failure.note}

---

## Blocked Items

| Run | Suite | Note | Last Updated |
|-----|-------|------|--------------|
| {blocked.run_name} ({blocked.run_pid}) | {blocked.suite_name} | {blocked.note} | {blocked.executed_at} |

---

## Data Quality Notes

{data_collection_issues — one bullet per issue}

---

## Recommendations

(Agent should generate 2-3 actionable recommendations based on the data)
```

## Follow-up Capabilities

After presenting the report, you can answer follow-up questions about the data.
You have the full JSON payload in context. Examples:

- "Tell me more about TR-1002" — look up the run PID in the failures or suites data
  and show all available detail.
- "Which suite has the worst pass rate?" — sort the suites array and report.
- "How many tests are still unexecuted?" — pull from summary.unexecuted.
- "Save this report to a file" — write the formatted markdown to a file like
  `reports/{cycle_pid}-{date}.md`.

Do not offer to do things the pipeline cannot support (e.g., comparing across cycles,
sending to Slack, updating qTest). If asked, explain it is out of scope for v1 and
suggest it as a future enhancement.
```

## Design Decision: Embedded Template

The report template is embedded directly in the skill file rather than stored in a separate file. This is a deliberate design choice:

**Why embed:**
- **Single file, zero dependencies.** The skill works with just one file drop. No risk of a missing template file breaking the skill.
- **Easier to version.** One file to review in a PR. The template and the instructions evolve together.
- **Agent reads it in one pass.** Claude Code loads the entire `.md` file into context. An external template would require an extra Read tool call, adding latency and a potential failure point.
- **The template is small.** At roughly 40 lines of markdown, it does not bloat the skill file.

**When to extract to a separate file:**
- If the template grows beyond 100 lines (e.g., adding charts, multiple sections, HTML formatting).
- If multiple skills need to share the same template.
- If non-engineers need to edit the template without touching the skill instructions.

For v1, embedding is the right call.

## Skill File Size Budget

Claude Code skill files are loaded into the agent's context window. The entire file counts against the available context. For the `/qtest-report` skill:

| Section | Estimated tokens |
|---------|-----------------|
| Title + arguments | ~30 |
| Instructions (6 steps) | ~400 |
| Report template | ~300 |
| Follow-up capabilities | ~150 |
| Error handling guidance | ~200 |
| **Total** | **~1,080 tokens** |

This is well within budget. A typical Claude Code context window is 200k tokens. The skill file consumes less than 1% of available context, leaving ample room for the JSON output (which could be large for cycles with hundreds of runs) and the formatted report.
