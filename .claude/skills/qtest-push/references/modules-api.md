# Modules API Reference

Use this to resolve a module name to its numeric ID before creating test cases.

## List All Modules (Full Tree)

```
GET /api/v3/projects/{projectId}/modules?expand=descendants
Authorization: Bearer {token}
```

Returns nested array of `ModuleResource` objects. Each module has:

| Field | Type | Description |
|---|---|---|
| `id` | integer | **Primary numeric ID** — use this as `parent_id` in test case creation |
| `pid` | string | Human-readable ID (e.g., `"MD-8"`) — use this in bulk `parent_module` field |
| `name` | string | Display name shown in qTest UI |
| `parent_id` | integer \| null | Parent module's ID; `null` for root-level modules |
| `children` | array | Nested child modules (only present with `?expand=descendants`) |

### Example Response

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

## Get Single Module

```
GET /api/v3/projects/{projectId}/modules/{moduleId}
Authorization: Bearer {token}
```

## Create a Module

```
POST /api/v3/projects/{projectId}/modules?parentId={parentModuleId}
Authorization: Bearer {token}
Content-Type: application/json

{ "name": "New Folder" }
```

Returns the created module with its assigned `id` and `pid`.

## Key Naming Difference

| Context | Field Name | Type | Notes |
|---|---|---|---|
| Creating a module | `parentId` query param | integer | camelCase — query parameter |
| Creating a test case | `parent_id` body field | integer | snake_case — JSON body field |
| Bulk test logs (Endpoint B) | `parent_module` body field | string | PID like `"MD-8"` or numeric ID as string |
