"""
Shared configuration for qTest API smoke tests.

Loads environment variables from .env file and provides:
  - Base URL construction
  - Session factory with auth headers
  - Common helper functions
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Load .env file from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# ---------------------------------------------------------------------------
# Configuration values
# ---------------------------------------------------------------------------
QTEST_DOMAIN = os.getenv("QTEST_DOMAIN", "")
QTEST_BASE_URL = os.getenv(
    "QTEST_BASE_URL",
    f"https://{QTEST_DOMAIN}.qtestnet.com" if QTEST_DOMAIN else "",
)
QTEST_BEARER_TOKEN = os.getenv("QTEST_BEARER_TOKEN", "")
QTEST_USERNAME = os.getenv("QTEST_USERNAME", "")
QTEST_PASSWORD = os.getenv("QTEST_PASSWORD", "")
QTEST_PROJECT_ID = os.getenv("QTEST_PROJECT_ID", "")


def validate_config():
    """Check that minimum required config is present. Exit with message if not."""
    errors = []
    if not QTEST_BASE_URL:
        errors.append("QTEST_DOMAIN or QTEST_BASE_URL must be set")
    if not QTEST_BEARER_TOKEN and not (QTEST_USERNAME and QTEST_PASSWORD):
        errors.append(
            "Either QTEST_BEARER_TOKEN or both QTEST_USERNAME + QTEST_PASSWORD must be set"
        )
    if not QTEST_PROJECT_ID:
        errors.append("QTEST_PROJECT_ID must be set")
    if errors:
        print("=" * 60)
        print("CONFIGURATION ERROR — check your .env file")
        print("=" * 60)
        for e in errors:
            print(f"  - {e}")
        print()
        print("Copy .env.example to .env and fill in your values.")
        sys.exit(1)


def get_api_base() -> str:
    """Return the fully-qualified API v3 project base URL."""
    return f"{QTEST_BASE_URL}/api/v3/projects/{QTEST_PROJECT_ID}"


def create_session() -> requests.Session:
    """
    Create a requests.Session pre-configured with auth headers.

    If QTEST_BEARER_TOKEN is set, uses that directly.
    Otherwise, performs login via POST /oauth/token.
    """
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })

    if QTEST_BEARER_TOKEN:
        session.headers["Authorization"] = f"Bearer {QTEST_BEARER_TOKEN}"
        return session

    # Login with username/password
    login_url = f"{QTEST_BASE_URL}/oauth/token"
    login_payload = {
        "grant_type": "password",
        "username": QTEST_USERNAME,
        "password": QTEST_PASSWORD,
    }
    login_headers = {"Content-Type": "application/x-www-form-urlencoded"}

    resp = session.post(login_url, data=login_payload, headers=login_headers)
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        print("ERROR: Login succeeded but no access_token in response.")
        print(f"Response: {json.dumps(resp.json(), indent=2)}")
        sys.exit(1)

    session.headers["Authorization"] = f"Bearer {token}"
    return session


def print_response_summary(resp: requests.Response, label: str = ""):
    """Pretty-print a response summary for smoke test output."""
    prefix = f"[{label}] " if label else ""
    print(f"{prefix}Status: {resp.status_code} {resp.reason}")
    print(f"{prefix}URL: {resp.request.method} {resp.url}")

    try:
        data = resp.json()
        if isinstance(data, list):
            print(f"{prefix}Response: array with {len(data)} items")
            if data:
                print(f"{prefix}First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'N/A'}")
        elif isinstance(data, dict):
            print(f"{prefix}Response keys: {list(data.keys())}")
        print(f"{prefix}Full JSON (truncated to 2000 chars):")
        formatted = json.dumps(data, indent=2)
        print(formatted[:2000])
        if len(formatted) > 2000:
            print(f"  ... ({len(formatted) - 2000} more characters)")
    except ValueError:
        print(f"{prefix}Response body (not JSON): {resp.text[:500]}")
    print()
