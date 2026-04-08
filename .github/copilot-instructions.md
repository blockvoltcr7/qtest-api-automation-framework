# GitHub Copilot Instructions — qTest API Automation Framework

This project automates interactions with the qTest Manager v3 REST API. Use these instructions whenever writing code that calls qTest APIs.

## Credentials — Always Read from .env

The project root `.env` file contains:

```
QTEST_DOMAIN=mycompany
QTEST_BEARER_TOKEN=eyJhbGci...
QTEST_PROJECT_ID=12345
```

`QTEST_DOMAIN` is the subdomain only — no `https://`, no `.com`. **Always** load credentials from `.env` using `python-dotenv` (Python) or `dotenv` (Node). Never hardcode credentials. The base URL is constructed as `https://{QTEST_DOMAIN}.qtestnet.com`.

### Python pattern

```python
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = f"https://{os.getenv('QTEST_DOMAIN')}.qtestnet.com"
TOKEN = os.getenv("QTEST_BEARER_TOKEN")
PROJECT_ID = os.getenv("QTEST_PROJECT_ID")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
```

---

## Push a Single Test Case

Use `POST /api/v3/projects/{projectId}/test-cases` to create one test case in a module.

```python
import requests

def push_single_test_case(module_id: int, name: str, steps: list[dict]) -> dict:
    """
    Push a single test case to a qTest module.

    Args:
        module_id: Numeric ID of the target module (folder)
        name: Display name of the test case
        steps: List of dicts with keys: description, expected, order

    Returns:
        Created test case dict with id, pid, web_url
    """
    payload = {
        "name": name,
        "parent_id": module_id,
        "properties": [],
        "test_steps": steps
    }
    response = requests.post(
        f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/test-cases",
        params={"parentId": module_id},
        headers=HEADERS,
        json=payload
    )
    response.raise_for_status()
    return response.json()
```

**Key fields:**
- `parent_id` (body, integer) — module ID for folder placement
- `parentId` (query param, integer) — same, takes precedence over body field
- `properties` — required, pass `[]` if no custom fields
- `test_steps` — each step: `{description, expected, order}`

---

## Push a Collection of Test Cases (Bulk)

Use `POST /api/v3/projects/{projectId}/auto-test-logs?type=automation` for bulk creation. This is asynchronous — poll the returned job ID.

```python
import time
import requests

def push_bulk_test_cases(test_cycle_pid: str, test_cases: list[dict]) -> str:
    """
    Push multiple test cases to qTest via auto-test-logs.

    Args:
        test_cycle_pid: PID of an existing Test Cycle e.g. "CL-1"
        test_cases: List of test case dicts (see payload structure below)

    Returns:
        Final job state: "SUCCESS" or "FAILED"
    """
    payload = {
        "test_cycle": test_cycle_pid,
        "execution_date": "2026-04-08T10:00:00Z",
        "test_logs": test_cases
    }
    response = requests.post(
        f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/auto-test-logs",
        params={"type": "automation"},
        headers=HEADERS,
        json=payload
    )
    response.raise_for_status()
    job_id = response.json()["id"]

    # Poll until complete
    while True:
        poll = requests.get(
            f"{BASE_URL}/api/v3/projects/queue-processing/{job_id}",
            headers=HEADERS
        )
        state = poll.json()["state"]
        if state in ("SUCCESS", "FAILED"):
            return state
        time.sleep(3)
```

**Each test case entry in `test_logs`:**

```python
{
    "name": "Verify login with valid credentials",
    "automation_content": "auth.login.ValidCredentials",  # unique dedup key
    "status": "UNEXECUTED",   # use UNEXECUTED to create without recording a result
    "exe_start_date": "2026-04-08T10:00:00Z",
    "exe_end_date": "2026-04-08T10:00:00Z",
    "module_names": ["Authentication", "Login"]  # folder path — created if missing
}
```

**Status values:** `PASSED` · `FAILED` · `SKIPPED` · `BLOCKED` · `INCOMPLETE` · `UNEXECUTED`

---

## Resolve a Module Name to Its Numeric ID

```python
def get_module_id(module_name: str) -> int | None:
    """Find a module's numeric ID by name."""
    response = requests.get(
        f"{BASE_URL}/api/v3/projects/{PROJECT_ID}/modules",
        params={"expand": "descendants"},
        headers=HEADERS
    )
    response.raise_for_status()

    def search(modules):
        for m in modules:
            if m["name"] == module_name:
                return m["id"]
            found = search(m.get("children", []))
            if found:
                return found
        return None

    return search(response.json())
```

---

## Common Error Handling

```python
response.raise_for_status()  # raises HTTPError for 4xx/5xx
```

| Code | Cause | Fix |
|---|---|---|
| `401` | Expired token | Regenerate `QTEST_BEARER_TOKEN` in qTest UI → Profile → API Access Tokens |
| `403` | No project access | Check `QTEST_PROJECT_ID` and user role |
| `404` | Bad project/module ID | Re-query modules API to verify IDs |
| `400` | Missing required field | Check `name` and `properties` are present |
| `413` | Payload too large | Split bulk payload into batches of < 500 |
