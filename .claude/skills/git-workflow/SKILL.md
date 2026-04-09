---
name: git-workflow
description: Analyze current code changes, generate a conventional commit message, then automatically stage all changes, commit, and push to the remote. Use when the user says "commit", "commit and push", "push my changes", "save my work to git", "/git_workflow_add_commit_push", or any variation of wanting to commit and push the current working state. Executes git add, commit, and push automatically without asking for confirmation.
---

# Git Workflow — Analyze, Commit, and Push

Automatically stage, commit, and push all current changes with a meaningful conventional commit message.

## Process

### Step 1 — Assess Current State

Run these in parallel:
```bash
git status
git diff
git log --oneline -5
```

Categorize changes:
- `feat` — new feature or functionality
- `fix` — bug fix
- `docs` — documentation only
- `refactor` — restructuring without behavior change
- `chore` — tooling, config, dependencies
- `test` — tests added or updated
- `style` — formatting only

### Step 2 — Review Changed Files

Read modified and new files to understand what changed. Group related changes together. Check for:
- Sensitive data (API keys, tokens, passwords) — abort and warn if found
- Unrelated changes that should be separate commits

### Step 3 — Craft the Commit Message

Follow conventional commits format:

```
<type>: <subject under 50 chars, imperative mood>

- What changed and why (bullet points)
- Any notable decisions or tradeoffs

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Subject line rules:** lowercase after type, no trailing period, imperative mood ("add" not "added"), under 50 characters.

### Step 4 — Execute (no confirmation needed)

```bash
git add .
git commit -m "<crafted message>"
git push origin <current-branch>
```

Report the commit hash and push result when done.

## Safety Rules

- Never commit `.env` files or files containing credentials
- Never force push (`--force`) unless explicitly requested
- Never skip hooks (`--no-verify`) unless explicitly requested
- If on a protected branch (main/master) and pushing, proceed — but note the branch in the output

## Output Format

Present before executing:

```
### Git Workflow Analysis

Current Status: N modified, N new, N deleted
Change type: <type>
Branch: <branch>

Change Summary:
- <what changed>

Commit Message:
  <type>: <subject>

  - <bullet>

Executing: git add . && git commit && git push...
```

Then run the commands and report the commit hash on success.
