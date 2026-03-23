#!/usr/bin/env python3
"""
Smoke Test 06 — Get Test Logs (Latest Execution Result)
=========================================================
Fetches the latest test log for a given test run, showing the most recent
execution result including status, timestamps, notes, and step-level details.

Also demonstrates fetching the full test log history for a run.

Endpoints tested:
  GET /api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs/last-run
  GET /api/v3/projects/{projectId}/test-runs/{testRunId}/test-logs

Usage:
  python 06_test_get_logs.py <TEST_RUN_ID>     # numeric ID
  python 06_test_get_logs.py 12345
"""

import sys
import json
from config import validate_config, create_session, get_api_base, print_response_summary


def get_latest_test_log(session, api_base, test_run_id, expand=None):
    """Fetch the latest (most recent) test log for a test run."""
    params = {}
    if expand:
        params["expand"] = expand  # e.g. "teststeplog.teststep"

    url = f"{api_base}/test-runs/{test_run_id}/test-logs/last-run"
    resp = session.get(url, params=params)
    print_response_summary(resp, label="Latest Test Log")
    if resp.status_code == 404:
        print("  (No test logs exist for this run — it may be unexecuted)")
        return None
    resp.raise_for_status()
    return resp.json()


def get_all_test_logs(session, api_base, test_run_id, page=1, page_size=25):
    """Fetch all test logs (execution history) for a test run."""
    params = {"page": page, "pageSize": page_size}
    url = f"{api_base}/test-runs/{test_run_id}/test-logs"
    resp = session.get(url, params=params)
    print_response_summary(resp, label="All Test Logs")
    resp.raise_for_status()
    return resp.json()


def test_get_logs(test_run_id):
    print("=" * 60)
    print(f"SMOKE TEST 06: Get Test Logs for Run ID {test_run_id}")
    print("=" * 60)
    print()

    session = create_session()
    api_base = get_api_base()

    # --- A) Get latest test log ---
    print("--- A) Latest Test Log (last-run) ---")
    latest = get_latest_test_log(session, api_base, test_run_id)
    if latest:
        status = latest.get("status", {})
        print(f"[PASS] Latest execution result:")
        print(f"  Status: {status.get('name', 'N/A')} (ID: {status.get('id', 'N/A')})")
        print(f"  Start:  {latest.get('exe_start_date', 'N/A')}")
        print(f"  End:    {latest.get('exe_end_date', 'N/A')}")
        print(f"  Note:   {(latest.get('note') or 'N/A')[:200]}")

        step_logs = latest.get("test_step_logs", [])
        if step_logs:
            print(f"  Step logs: {len(step_logs)} step(s)")
            for sl in step_logs[:5]:
                sl_status = sl.get("status", "N/A")
                print(f"    Step {sl.get('order', '?')}: {sl_status}")

        print()
        print("Full latest log response:")
        print(json.dumps(latest, indent=2)[:3000])
    else:
        print("[INFO] No execution logs found for this test run.")
    print()

    # --- B) Get latest with step details expanded ---
    print("--- B) Latest Test Log (with step details expanded) ---")
    latest_expanded = get_latest_test_log(
        session, api_base, test_run_id, expand="teststeplog.teststep"
    )
    if latest_expanded:
        step_logs = latest_expanded.get("test_step_logs", [])
        print(f"[PASS] Retrieved with {len(step_logs)} expanded step log(s).")
        for sl in step_logs[:3]:
            print(f"  Step {sl.get('order', '?')}: status={sl.get('status', 'N/A')}, "
                  f"description={str(sl.get('description', ''))[:80]}")
    print()

    # --- C) Get all test logs (history) ---
    print("--- C) All Test Logs (execution history) ---")
    all_logs = get_all_test_logs(session, api_base, test_run_id)
    if isinstance(all_logs, list):
        print(f"[PASS] Found {len(all_logs)} total execution(s) in history.")
        for log in all_logs[:5]:
            s = log.get("status", {})
            print(f"  {log.get('exe_start_date', 'N/A')} — {s.get('name', 'N/A')}")
    elif isinstance(all_logs, dict):
        # Some versions return paginated wrapper
        items = all_logs.get("items", all_logs.get("test_logs", []))
        total = all_logs.get("total", len(items))
        print(f"[PASS] Found {total} total execution(s) in history (paginated).")

    print()
    print("=" * 60)
    return True


if __name__ == "__main__":
    validate_config()
    if len(sys.argv) < 2:
        print("Usage: python 06_test_get_logs.py <TEST_RUN_ID>")
        print("Example: python 06_test_get_logs.py 12345")
        print()
        print("Note: Use a numeric test run ID (not a PID).")
        print("Get IDs from the output of 04_test_get_runs.py")
        sys.exit(1)
    test_get_logs(int(sys.argv[1]))
