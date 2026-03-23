#!/usr/bin/env python3
"""
Smoke Test 02 — Get Test Cycles & Resolve PID
===============================================
Fetches all test cycles in the project and demonstrates how to resolve
a human-readable PID (e.g. "CL-416") to its numeric internal ID.

Endpoints tested:
  GET /api/v3/projects/{projectId}/test-cycles
  GET /api/v3/projects/{projectId}/test-cycles?expand=descendants
  GET /api/v3/projects/{projectId}/test-cycles/{testCycleId}

Usage:
  python 02_test_get_cycles.py
  python 02_test_get_cycles.py CL-416        # resolve a specific PID
"""

import sys
import json
from config import validate_config, create_session, get_api_base, print_response_summary


def get_all_cycles(session, api_base, expand_descendants=False):
    """Fetch all test cycles at root level."""
    params = {}
    if expand_descendants:
        params["expand"] = "descendants"

    url = f"{api_base}/test-cycles"
    resp = session.get(url, params=params)
    print_response_summary(resp, label="Get All Cycles")
    resp.raise_for_status()
    return resp.json()


def get_cycle_by_id(session, api_base, cycle_id, expand_descendants=False):
    """Fetch a single test cycle by its numeric ID."""
    params = {}
    if expand_descendants:
        params["expand"] = "descendants"

    url = f"{api_base}/test-cycles/{cycle_id}"
    resp = session.get(url, params=params)
    print_response_summary(resp, label=f"Get Cycle {cycle_id}")
    resp.raise_for_status()
    return resp.json()


def find_cycle_by_pid(cycles, target_pid):
    """
    Search a list of test cycle objects for one matching a PID.
    Also searches nested children if 'test_cycles' key exists (from expand=descendants).
    """
    for cycle in cycles:
        if cycle.get("pid") == target_pid:
            return cycle
        # Check nested child cycles (from expand=descendants)
        children = cycle.get("test_cycles", [])
        if children:
            found = find_cycle_by_pid(children, target_pid)
            if found:
                return found
    return None


def test_get_cycles(target_pid=None):
    print("=" * 60)
    print("SMOKE TEST 02: Get Test Cycles & Resolve PID")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    # --- Test A: Get all cycles (flat) ---
    print("--- A) Get all cycles (flat, no descendants) ---")
    cycles = get_all_cycles(session, api_base, expand_descendants=False)
    print(f"[PASS] Retrieved {len(cycles)} top-level test cycle(s).")
    print()
    for c in cycles[:5]:
        print(f"  PID: {c.get('pid', 'N/A'):<12} ID: {c.get('id', 'N/A'):<10} Name: {c.get('name', 'N/A')}")
    if len(cycles) > 5:
        print(f"  ... and {len(cycles) - 5} more")
    print()

    # --- Test B: Get all cycles with descendants ---
    print("--- B) Get all cycles (with expand=descendants) ---")
    cycles_full = get_all_cycles(session, api_base, expand_descendants=True)
    print(f"[PASS] Retrieved {len(cycles_full)} top-level cycle(s) with descendants expanded.")
    print()

    # Show hierarchy for first cycle
    if cycles_full:
        sample = cycles_full[0]
        print(f"  Sample cycle: {sample.get('pid')} - {sample.get('name')}")
        child_cycles = sample.get("test_cycles", [])
        child_suites = sample.get("test_suites", [])
        print(f"    Child cycles: {len(child_cycles)}")
        print(f"    Child suites: {len(child_suites)}")
        for ts in child_suites[:3]:
            print(f"      Suite: {ts.get('pid', 'N/A')} - {ts.get('name', 'N/A')}")
    print()

    # --- Test C: Resolve a PID ---
    if target_pid:
        print(f"--- C) Resolve PID '{target_pid}' to numeric ID ---")
        found = find_cycle_by_pid(cycles_full, target_pid)
        if found:
            print(f"[PASS] Found: PID={found['pid']} → ID={found['id']}")
            print(f"  Name: {found.get('name')}")
            print(f"  Web URL: {found.get('web_url', 'N/A')}")
            print(f"  Full object:")
            # Print without deeply nested children for readability
            display = {k: v for k, v in found.items() if k not in ("test_cycles", "test_suites")}
            print(json.dumps(display, indent=2))
        else:
            print(f"[WARN] PID '{target_pid}' not found in {len(cycles_full)} cycle(s).")
            print("  Available PIDs:")
            for c in cycles_full[:10]:
                print(f"    {c.get('pid')}")
    else:
        print("--- C) Skipped PID resolution (no PID argument provided) ---")
        print("  Tip: Run with a PID argument, e.g.: python 02_test_get_cycles.py CL-416")

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    pid_arg = sys.argv[1] if len(sys.argv) > 1 else None
    test_get_cycles(target_pid=pid_arg)
