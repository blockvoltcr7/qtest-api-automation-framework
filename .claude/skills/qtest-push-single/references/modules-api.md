# Modules API — Resolve Folder Names to IDs

## List Full Module Tree

```
GET /api/v3/projects/{projectId}/modules?expand=descendants
Authorization: Bearer {token}
```

Returns nested array. Each module has:

| Field | Type | Description |
|---|---|---|
| `id` | integer | **Use this as `parent_id`** in test case creation |
| `pid` | string | Human-readable ID e.g. `"MD-8"` |
| `name` | string | Display name shown in qTest UI |
| `parent_id` | integer \| null | Parent module's `id`; `null` for root-level |
| `children` | array | Nested child modules |

## Example Response

```json
[
  {
    "id": 2107600,
    "name": "Authentication",
    "pid": "MD-1",
    "parent_id": null,
    "children": [
      {
        "id": 2107619,
        "name": "Login",
        "pid": "MD-8",
        "parent_id": 2107600,
        "children": []
      }
    ]
  }
]
```

## curl Example

```bash
curl -s \
  "https://${QTEST_DOMAIN}.qtestnet.com/api/v3/projects/${QTEST_PROJECT_ID}/modules?expand=descendants" \
  -H "Authorization: Bearer ${QTEST_BEARER_TOKEN}" \
  | jq '.[] | {id, name, pid}'
```
