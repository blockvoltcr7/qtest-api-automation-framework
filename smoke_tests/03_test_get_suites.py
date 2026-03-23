#!/usr/bin/env python3
"""
Smoke Test 03 — Get Test Suites Under a Test Cycle
====================================================
Given a test cycle PID (e.g. "CL-416"), resolves it to a numeric ID
and fetches all test suites nested under it.

Endpoints tested:
  GET /api/v3/projects/{projectId}/test-cycles?expand=descendants
  GET /api/v3/projects/{projectId}/test-suites?parentId={id}&parentType=test-cycle

Usage:
  python 03_test_get_suites.py CL-416
"""

import sys
import json
from config import validate_config, create_session, get_api_base, print_response_summary


def resolve_pid_to_id(session, api_base, target_pid):
    """Fetch all cycles with descendants and find the one matching the PID."""
    resp = session.get(f"{api_base}/test-cycles", params={"expand": "descendants"})
    resp.raise_for_status()
    cycles = resp.json()

    def search(items):
        for c in items:
            if c.get("pid") == target_pid:
                return c
            found = search(c.get("test_cycles", []))
            if found:
                return found
        return None

    return search(cycles)


def get_test_suites(session, api_base, parent_id, parent_type="test-cycle"):
    """Fetch test suites under a given parent (cycle or release)."""
    params = {
        "parentId": parent_id,
        "parentType": parent_type,
    }
    url = f"{api_base}/test-suites"
    resp = session.get(url, params=params)
    print_response_summary(resp, label="Get Test Suites")
    resp.raise_for_status()
    return resp.json()


def test_get_suites(cycle_pid):
    print("=" * 60)
    print(f"SMOKE TEST 03: Get Test Suites Under '{cycle_pid}'")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    # Step 1: Resolve PID
    print(f"Step 1: Resolving '{cycle_pid}' to numeric ID ...")
    cycle = resolve_pid_to_id(session, api_base, cycle_pid)
    if not cycle:
        print(f"[FAIL] Could not find cycle with PID '{cycle_pid}'")
        return False

    cycle_id = cycle["id"]
    print(f"[PASS] Resolved: {cycle_pid} → ID {cycle_id} ('{cycle['name']}')")
    print()

    # Step 2: Get test suites
    print(f"Step 2: Fetching test suites under cycle ID {cycle_id} ...")
    suites = get_test_suites(session, api_base, cycle_id)

    if not suites:
        print("[WARN] No test suites found under this cycle.")
        print("  The cycle may contain test runs directly, or nested sub-cycles.")
        return True

    print(f"[PASS] Found {len(suites)} test suite(s):")
    print()
    print(f"  {'PID':<12} {'ID':<10} {'Name'}")
    print(f"  {'-'*12} {'-'*10} {'-'*40}")
    for suite in suites:
        print(f"  {suite.get('pid', 'N/A'):<12} {suite.get('id', 'N/A'):<10} {suite.get('name', 'N/A')}")

    print()
    print("Sample test suite response object:")
    if suites:
        # Show full structure of first suite (for schema reference)
        print(json.dumps(suites[0], indent=2))

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    if len(sys.argv) < 2:
        print("Usage: python 03_test_get_suites.py <CYCLE_PID>")
        print("Example: python 03_test_get_suites.py CL-416")
        sys.exit(1)
    test_get_suites(sys.argv[1])
