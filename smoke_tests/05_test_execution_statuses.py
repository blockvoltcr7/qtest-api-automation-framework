#!/usr/bin/env python3
"""
Smoke Test 05 — Get Execution Statuses
========================================
Retrieves the project's configured execution statuses (Passed, Failed,
Blocked, Incomplete, Unexecuted, plus any custom statuses).

This is a reference lookup — you need these to map status IDs to names
when aggregating statistics from test runs.

Endpoints tested:
  GET /api/v3/projects/{projectId}/test-runs/execution-statuses

Usage:
  python 05_test_execution_statuses.py
"""

import json
from config import validate_config, create_session, get_api_base, print_response_summary


def get_execution_statuses(session, api_base):
    """Fetch all execution status definitions for the project."""
    url = f"{api_base}/test-runs/execution-statuses"
    resp = session.get(url)
    print_response_summary(resp, label="Execution Statuses")
    resp.raise_for_status()
    return resp.json()


def test_execution_statuses():
    print("=" * 60)
    print("SMOKE TEST 05: Get Execution Statuses")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    statuses = get_execution_statuses(session, api_base)

    if not statuses:
        print("[WARN] No execution statuses returned. This is unexpected.")
        return False

    print(f"[PASS] Retrieved {len(statuses)} execution status(es):")
    print()
    print(f"  {'ID':<8} {'Name':<20} {'Color':<12} {'Default?'}")
    print(f"  {'-'*8} {'-'*20} {'-'*12} {'-'*8}")
    for s in statuses:
        default = "YES" if s.get("is_default") else ""
        print(f"  {s.get('id', 'N/A'):<8} {s.get('name', 'N/A'):<20} {s.get('color', 'N/A'):<12} {default}")

    print()
    print("Full response (for schema reference):")
    print(json.dumps(statuses, indent=2))

    print()
    print("STATUS ID → NAME MAPPING (use this for aggregation):")
    mapping = {s["id"]: s["name"] for s in statuses}
    print(f"  {json.dumps(mapping, indent=4)}")

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    test_execution_statuses()
