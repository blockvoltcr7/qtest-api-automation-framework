#!/usr/bin/env python3
"""
Smoke Test 07 — Full End-to-End Flow: Test Cycle → Suites → Stats
===================================================================
The complete scenario: given a Test Cycle PID like "CL-416", retrieves
all test suites, all test runs within those suites, and computes
execution statistics (pass/fail/blocked/etc counts).

This is the integration test that exercises the entire API call chain.

Endpoints tested (in order):
  1. GET .../test-cycles?expand=descendants        → resolve PID
  2. GET .../test-suites?parentId=X&parentType=test-cycle  → get suites
  3. GET .../test-runs?parentId=Y&parentType=test-suite    → get runs (per suite)
  4. GET .../test-runs/execution-statuses           → status reference
  5. Client-side aggregation                        → compute stats

Usage:
  python 07_test_full_flow.py CL-416
"""

import sys
import json
from collections import Counter
from config import validate_config, create_session, get_api_base, print_response_summary


def resolve_cycle_pid(session, api_base, target_pid):
    """Find a test cycle by PID, searching the full hierarchy."""
    resp = session.get(f"{api_base}/test-cycles", params={"expand": "descendants"})
    resp.raise_for_status()

    def search(items):
        for c in items:
            if c.get("pid") == target_pid:
                return c
            found = search(c.get("test_cycles", []))
            if found:
                return found
        return None

    return search(resp.json())


def get_test_suites(session, api_base, cycle_id):
    """Get all test suites under a test cycle."""
    resp = session.get(
        f"{api_base}/test-suites",
        params={"parentId": cycle_id, "parentType": "test-cycle"},
    )
    resp.raise_for_status()
    return resp.json()


def get_test_runs_paginated(session, api_base, parent_id, parent_type, page_size=100):
    """
    Get ALL test runs under a parent, handling pagination.
    Returns the complete list across all pages.
    """
    all_runs = []
    page = 1

    while True:
        resp = session.get(
            f"{api_base}/test-runs",
            params={
                "parentId": parent_id,
                "parentType": parent_type,
                "page": page,
                "pageSize": page_size,
            },
        )
        resp.raise_for_status()
        runs = resp.json()

        if not runs:
            break

        all_runs.extend(runs)

        if len(runs) < page_size:
            break  # Last page
        page += 1

    return all_runs


def get_execution_statuses(session, api_base):
    """Get the status ID → name mapping."""
    resp = session.get(f"{api_base}/test-runs/execution-statuses")
    resp.raise_for_status()
    return {s["id"]: s["name"] for s in resp.json()}


def extract_status_from_run(run, status_map):
    """
    Extract the execution status name from a test run object.

    The status can appear in different places depending on the qTest version:
      - run["properties"] array with field_name="Status"
      - run["latest_test_log"]["status"]["id"]
      - run["exe_status"] (some versions)

    Returns the status name string, or "Unknown".
    """
    # Approach 1: Check properties array
    props = run.get("properties", [])
    if isinstance(props, list):
        for prop in props:
            field = prop.get("field_name", "") or prop.get("label", "")
            if field.lower() == "status":
                # field_value_name is the display name
                name = prop.get("field_value_name")
                if name:
                    return name
                # field_value might be the status ID
                val = prop.get("field_value")
                if val and isinstance(val, (int, str)):
                    return status_map.get(int(val), f"ID:{val}")

    # Approach 2: Check latest_test_log if present
    log = run.get("latest_test_log") or run.get("test_log")
    if log and isinstance(log, dict):
        status_obj = log.get("status", {})
        if status_obj:
            return status_obj.get("name", status_map.get(status_obj.get("id"), "Unknown"))

    # Approach 3: Check exe_status or status field
    exe_status = run.get("exe_status")
    if exe_status:
        return status_map.get(exe_status, f"ID:{exe_status}")

    return "Unknown"


def test_full_flow(cycle_pid):
    print("=" * 60)
    print(f"SMOKE TEST 07: Full Flow — {cycle_pid} → Suites → Stats")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    # ---------------------------------------------------------------
    # Step 1: Resolve cycle PID
    # ---------------------------------------------------------------
    print(f"[1/5] Resolving cycle PID '{cycle_pid}' ...")
    cycle = resolve_cycle_pid(session, api_base, cycle_pid)
    if not cycle:
        print(f"[FAIL] Could not find cycle with PID '{cycle_pid}'")
        return False
    cycle_id = cycle["id"]
    print(f"  → {cycle_pid} = ID {cycle_id} ('{cycle['name']}')")
    print()

    # ---------------------------------------------------------------
    # Step 2: Get test suites
    # ---------------------------------------------------------------
    print(f"[2/5] Fetching test suites under {cycle_pid} ...")
    suites = get_test_suites(session, api_base, cycle_id)
    print(f"  → Found {len(suites)} test suite(s)")
    for s in suites:
        print(f"    {s.get('pid', 'N/A'):<12} {s.get('name', 'N/A')}")
    print()

    # ---------------------------------------------------------------
    # Step 3: Get test runs for each suite
    # ---------------------------------------------------------------
    print(f"[3/5] Fetching test runs for each suite ...")
    suite_runs = {}  # suite_pid → list of runs
    all_runs = []

    for suite in suites:
        suite_pid = suite.get("pid", f"ID:{suite['id']}")
        runs = get_test_runs_paginated(session, api_base, suite["id"], "test-suite")
        suite_runs[suite_pid] = runs
        all_runs.extend(runs)
        print(f"    {suite_pid}: {len(runs)} test run(s)")

    # Also get runs directly under the cycle (not inside any suite)
    direct_runs = get_test_runs_paginated(session, api_base, cycle_id, "test-cycle")
    if direct_runs:
        suite_runs["(direct under cycle)"] = direct_runs
        all_runs.extend(direct_runs)
        print(f"    (direct under cycle): {len(direct_runs)} test run(s)")

    print(f"  → Total: {len(all_runs)} test run(s)")
    print()

    # ---------------------------------------------------------------
    # Step 4: Get execution statuses reference
    # ---------------------------------------------------------------
    print(f"[4/5] Fetching execution status definitions ...")
    status_map = get_execution_statuses(session, api_base)
    print(f"  → {len(status_map)} status(es): {list(status_map.values())}")
    print()

    # ---------------------------------------------------------------
    # Step 5: Aggregate statistics
    # ---------------------------------------------------------------
    print(f"[5/5] Computing statistics ...")
    print()

    # Overall stats
    overall_stats = Counter()
    for run in all_runs:
        status_name = extract_status_from_run(run, status_map)
        overall_stats[status_name] += 1

    total = sum(overall_stats.values())
    print(f"  ┌─────────────────────────────────────────────────┐")
    print(f"  │  OVERALL STATISTICS for {cycle_pid:<26}│")
    print(f"  ├─────────────────────────────────────────────────┤")
    print(f"  │  Total Test Runs: {total:<30}│")
    print(f"  ├──────────────────────┬──────────┬───────────────┤")
    print(f"  │  Status              │  Count   │  Percentage   │")
    print(f"  ├──────────────────────┼──────────┼───────────────┤")
    for status_name in sorted(overall_stats.keys()):
        count = overall_stats[status_name]
        pct = (count / total * 100) if total > 0 else 0
        print(f"  │  {status_name:<20}│  {count:<8}│  {pct:>6.1f}%      │")
    print(f"  └──────────────────────┴──────────┴───────────────┘")
    print()

    # Per-suite breakdown
    print("  PER-SUITE BREAKDOWN:")
    print(f"  {'Suite':<14} ", end="")
    all_status_names = sorted(set(s for s in overall_stats.keys()))
    for sn in all_status_names:
        print(f"{sn:<14}", end="")
    print("Total")
    print(f"  {'-'*14} ", end="")
    for _ in all_status_names:
        print(f"{'-'*14}", end="")
    print(f"{'-'*8}")

    for suite_pid, runs in suite_runs.items():
        suite_stats = Counter()
        for run in runs:
            suite_stats[extract_status_from_run(run, status_map)] += 1
        print(f"  {suite_pid:<14} ", end="")
        for sn in all_status_names:
            print(f"{suite_stats.get(sn, 0):<14}", end="")
        print(f"{len(runs)}")

    print()

    # Output as JSON (for agent consumption)
    result = {
        "cycle_pid": cycle_pid,
        "cycle_id": cycle_id,
        "cycle_name": cycle["name"],
        "total_runs": total,
        "overall_stats": dict(overall_stats),
        "suites": [
            {
                "pid": s.get("pid"),
                "id": s.get("id"),
                "name": s.get("name"),
                "run_count": len(suite_runs.get(s.get("pid", ""), [])),
            }
            for s in suites
        ],
    }
    print("  JSON OUTPUT (for agent skill consumption):")
    print(json.dumps(result, indent=2))

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    if len(sys.argv) < 2:
        print("Usage: python 07_test_full_flow.py <CYCLE_PID>")
        print("Example: python 07_test_full_flow.py CL-416")
        sys.exit(1)
    test_full_flow(sys.argv[1])
