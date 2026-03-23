#!/usr/bin/env python3
"""
Smoke Test 04 — Get Test Runs Under a Test Suite
==================================================
Given a test suite PID (e.g. "TC-970"), fetches all test runs inside it.
Also demonstrates fetching test runs directly under a test cycle.

Endpoints tested:
  GET /api/v3/projects/{projectId}/test-runs?parentId={id}&parentType=test-suite
  GET /api/v3/projects/{projectId}/test-runs?parentId={id}&parentType=test-cycle

Usage:
  python 04_test_get_runs.py TC-970             # runs under a test suite
  python 04_test_get_runs.py CL-416 --cycle     # runs directly under a cycle
"""

import sys
import json
from config import validate_config, create_session, get_api_base, print_response_summary


def resolve_suite_pid(session, api_base, target_pid):
    """
    Resolve a test suite PID (TC-xxx) by searching all cycles with descendants.
    Test suites appear nested inside test cycles when expand=descendants is used.
    """
    resp = session.get(f"{api_base}/test-cycles", params={"expand": "descendants"})
    resp.raise_for_status()
    cycles = resp.json()

    def search_suites(items):
        for c in items:
            # Check suites inside this cycle
            for s in c.get("test_suites", []):
                if s.get("pid") == target_pid:
                    return s
            # Recurse into child cycles
            found = search_suites(c.get("test_cycles", []))
            if found:
                return found
        return None

    return search_suites(cycles)


def resolve_cycle_pid(session, api_base, target_pid):
    """Resolve a test cycle PID (CL-xxx)."""
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


def get_test_runs(session, api_base, parent_id, parent_type, page=1, page_size=100):
    """Fetch test runs under a parent container, with pagination."""
    params = {
        "parentId": parent_id,
        "parentType": parent_type,
        "page": page,
        "pageSize": page_size,
    }
    url = f"{api_base}/test-runs"
    resp = session.get(url, params=params)
    print_response_summary(resp, label=f"Get Runs (page {page})")
    resp.raise_for_status()
    return resp.json()


def test_get_runs(target_pid, is_cycle=False):
    print("=" * 60)
    parent_type_label = "Test Cycle" if is_cycle else "Test Suite"
    print(f"SMOKE TEST 04: Get Test Runs Under {parent_type_label} '{target_pid}'")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    # Step 1: Resolve PID to numeric ID
    print(f"Step 1: Resolving {parent_type_label} PID '{target_pid}' ...")
    if is_cycle:
        parent = resolve_cycle_pid(session, api_base, target_pid)
        parent_type = "test-cycle"
    else:
        parent = resolve_suite_pid(session, api_base, target_pid)
        parent_type = "test-suite"

    if not parent:
        print(f"[FAIL] Could not find {parent_type_label} with PID '{target_pid}'")
        return False

    parent_id = parent["id"]
    print(f"[PASS] Resolved: {target_pid} → ID {parent_id} ('{parent.get('name', 'N/A')}')")
    print()

    # Step 2: Fetch test runs (first page)
    print(f"Step 2: Fetching test runs under {parent_type} ID {parent_id} ...")
    runs = get_test_runs(session, api_base, parent_id, parent_type)

    if not runs:
        print("[WARN] No test runs found under this container.")
        return True

    print(f"[PASS] Found {len(runs)} test run(s) on page 1:")
    print()
    print(f"  {'PID':<12} {'ID':<10} {'Name':<40} {'Status'}")
    print(f"  {'-'*12} {'-'*10} {'-'*40} {'-'*15}")

    for run in runs[:20]:  # Show first 20
        # Status can be in properties array or as a direct field — handle both
        status = "N/A"
        props = run.get("properties", [])
        if isinstance(props, list):
            for prop in props:
                if prop.get("field_name") == "Status" or prop.get("field_id") == "status":
                    status = prop.get("field_value_name", prop.get("field_value", "N/A"))
                    break
        print(f"  {run.get('pid', 'N/A'):<12} {run.get('id', 'N/A'):<10} {run.get('name', 'N/A')[:40]:<40} {status}")

    if len(runs) > 20:
        print(f"  ... and {len(runs) - 20} more")
    print()

    # Show raw structure of first run
    if runs:
        print("Sample test run response object (first item):")
        print(json.dumps(runs[0], indent=2)[:3000])
        print()

    # Step 3: Pagination check
    if len(runs) >= 100:
        print("[INFO] Results may be paginated (100 returned). Use page=2 for more.")

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python 04_test_get_runs.py TC-970           # runs under a test suite")
        print("  python 04_test_get_runs.py CL-416 --cycle   # runs under a test cycle")
        sys.exit(1)

    is_cycle = "--cycle" in sys.argv
    target = sys.argv[1]
    test_get_runs(target, is_cycle=is_cycle)
