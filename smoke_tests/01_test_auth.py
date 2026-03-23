#!/usr/bin/env python3
"""
Smoke Test 01 — Authentication
===============================
Validates that we can authenticate with the qTest API and receive a valid
Bearer token. Tests both token-based and login-based auth flows.

Expected output on success:
  - HTTP 200 from a simple GET /api/v3/projects call
  - List of accessible projects returned

Usage:
  python 01_test_auth.py
"""

import json
import requests
from config import (
    validate_config,
    create_session,
    get_api_base,
    print_response_summary,
    QTEST_BASE_URL,
    QTEST_BEARER_TOKEN,
)


def test_auth():
    print("=" * 60)
    print("SMOKE TEST 01: Authentication")
    print("=" * 60)

    # Show which auth method is being used
    if QTEST_BEARER_TOKEN:
        print("Auth method: Pre-configured Bearer token")
    else:
        print("Auth method: Username/password login (POST /oauth/token)")
    print()

    # Create an authenticated session
    session = create_session()
    print("[PASS] Session created successfully with auth headers.")
    print(f"  Authorization header present: {'Authorization' in session.headers}")
    print()

    # Verify by hitting a lightweight endpoint: list projects
    print("Verifying token by calling GET /api/v3/projects ...")
    resp = session.get(f"{QTEST_BASE_URL}/api/v3/projects")
    print_response_summary(resp, label="Projects")

    if resp.status_code == 200:
        projects = resp.json()
        print(f"[PASS] Token is valid. {len(projects)} project(s) accessible.")
        print()
        print("Accessible projects:")
        for p in projects[:10]:  # Show first 10
            print(f"  ID: {p.get('id'):<10} Name: {p.get('name', 'N/A')}")
        if len(projects) > 10:
            print(f"  ... and {len(projects) - 10} more")
    elif resp.status_code == 401:
        print("[FAIL] 401 Unauthorized — token is invalid or expired.")
        print("  Check your QTEST_BEARER_TOKEN or credentials in .env")
    elif resp.status_code == 429:
        print("[WARN] 429 Rate limited — too many requests. Try again shortly.")
    else:
        print(f"[FAIL] Unexpected status code: {resp.status_code}")

    print()
    print("=" * 60)
    return resp.status_code == 200


if __name__ == "__main__":
    validate_config()
    success = test_auth()
    exit(0 if success else 1)
