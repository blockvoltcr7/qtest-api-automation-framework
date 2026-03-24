# Phase 2: Resolve Cycle PID

## Purpose

Convert a human-readable test cycle PID (e.g., "CL-416") into the numeric `cycle_id` that all subsequent API calls require. Also captures the cycle name for the report header.

---

## API Call

```
GET /api/v3/projects/{projectId}/test-cycles?expand=descendants
```

### Why `expand=descendants`?

qTest Manager has no direct PID lookup endpoint. There is no `GET /test-cycles?pid=CL-416`. Instead, you must:

1. Fetch the entire test cycle tree for the project
2. Search it client-side for the target PID

The `expand=descendants` query parameter tells qTest to return the full nested hierarchy in a single response. Without it, you would only get top-level cycles and would need separate API calls to fetch children at each depth level.

This is a single API call that returns the complete tree, regardless of depth. The tradeoff is that the response can be large for projects with hundreds of cycles, but it avoids the alternative of making N recursive API calls.

---

## Input

- `cycle_pid`: string, e.g., `"CL-416"`
- `session`: authenticated `requests.Session` from Phase 1
- `api_base`: project API base URL from `get_api_base()`

---

## Output

A dictionary with three fields:

```python
{
    "cycle_id": 67890,       # int -- used by Phase 3 API calls
    "cycle_name": "Sprint 42 Regression Cycle",  # str -- used in report header
    "cycle_pid": "CL-416"    # str -- echo back for confirmation
}
```

---

## Algorithm: Recursive Depth-First Search

The qTest API returns test cycles as a nested tree. Each cycle object has an optional `test_cycles` array containing its children. The search traverses this tree depth-first looking for a matching PID.

### Code Reference

**File**: `smoke_tests/07_test_full_flow.py`, lines 28-42

```python
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
```

### Pseudocode Walkthrough

```
FUNCTION resolve_cycle_pid(session, api_base, target_pid):
    response = GET /test-cycles?expand=descendants
    tree = response.json()    # array of top-level cycle objects

    FUNCTION search(items):
        FOR each cycle IN items:
            IF cycle.pid == target_pid:
                RETURN cycle          # Found it
            result = search(cycle.test_cycles)   # Recurse into children
            IF result IS NOT None:
                RETURN result          # Found in subtree
        RETURN None                    # Not found at this level

    RETURN search(tree)
```

### Example Tree Structure

```json
[
  {
    "id": 100,
    "pid": "CL-1",
    "name": "Release 5.0",
    "test_cycles": [
      {
        "id": 200,
        "pid": "CL-200",
        "name": "Sprint 41",
        "test_cycles": []
      },
      {
        "id": 300,
        "pid": "CL-416",
        "name": "Sprint 42 Regression Cycle",
        "test_cycles": [
          {
            "id": 400,
            "pid": "CL-417",
            "name": "Sub-cycle A",
            "test_cycles": []
          }
        ]
      }
    ]
  }
]
```

For `target_pid = "CL-416"`, the search path is:
1. Check CL-1 -- no match
2. Recurse into CL-1's children
3. Check CL-200 -- no match
4. Check CL-416 -- match found, return this object

---

## Edge Cases

### PID Not Found

If `resolve_cycle_pid()` returns `None`, the pipeline should abort with a helpful error. The enhanced version in the pipeline script will list available PIDs:

```python
if not cycle:
    # Collect all PIDs from the tree for the error message
    all_pids = []
    def collect_pids(items):
        for c in items:
            all_pids.append(f"  {c.get('pid', 'N/A'):<12} {c.get('name', 'N/A')}")
            collect_pids(c.get("test_cycles", []))
    collect_pids(resp.json())

    print(f"ERROR: Cycle PID '{target_pid}' not found.", file=sys.stderr)
    print(f"Available cycles:", file=sys.stderr)
    for line in all_pids[:20]:
        print(line, file=sys.stderr)
    sys.exit(1)
```

### Multiple Cycles with Same PID

This should not happen in a well-configured qTest instance, but if it does, the DFS returns the first match encountered. This is a known limitation.

**Documented behavior**: First match wins, depth-first from the top of the tree. The pipeline does not detect or warn about duplicates.

### Very Large Cycle Tree

The `expand=descendants` parameter returns the entire tree in one response. For projects with thousands of cycles, this response can be several megabytes. However:
- It is still a single API call (no pagination needed)
- The DFS search is O(n) where n = total cycles, which is fast even for large trees
- Memory usage is bounded by the JSON response size

### Cycle at Root Level

Some cycles may not be nested under any parent. These appear as top-level items in the response array. The search handles this naturally since it starts at the root.

---

## Failure Mode

| Failure | Cause | Behavior |
|---------|-------|----------|
| API returns 401/403 | Token expired or insufficient permissions | `raise_for_status()` raises HTTPError, script exits |
| API returns 500 | qTest server error | `raise_for_status()` raises HTTPError, script exits |
| PID not found | Typo or wrong project | Fatal error with list of available PIDs |
| Empty response | Project has no test cycles | Fatal error: "No test cycles found in project" |
