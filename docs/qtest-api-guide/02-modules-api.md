# Modules API

A **module** is a folder in qTest Manager's Test Design tree. Every test case belongs to a module. Before creating test cases in a specific folder, you must retrieve that folder's numeric `id`.

This document covers the module endpoints needed to discover and manage the folder structure.

---

## Key Concepts

| Term | Meaning |
|---|---|
| `id` | The primary numeric identifier for a module (e.g., `2107619`). This is the value used in all API requests via the `parent_id` field. |
| `pid` | The human-readable project-scoped identifier (e.g., `"MD-8"`). Displayed in the qTest UI. Can also be used in some bulk endpoints. |
| `parent_id` | The `id` of the parent module. Absent or `null` for root-level modules. |
| `children` | Array of nested child modules (only present when `?expand=descendants` is used). |

---

## 1. List All Modules (Full Tree)

Retrieve the complete module hierarchy for a project in a single call.

### Endpoint

```
GET /api/v3/projects/{projectId}/modules?expand=descendants
```

### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `projectId` | integer (int64) | Yes | Numeric ID of the qTest project |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expand` | string | No | Pass `"descendants"` to return the full nested tree recursively |
| `parentId` | integer (int64) | No | If omitted, returns root-level modules. Pass a module `id` to get only that subtree. |

### Request Example

```http
GET https://mycompany.qtestnet.com/api/v3/projects/12345/modules?expand=descendants
Authorization: Bearer {access_token}
```

### Response — `200 OK`

Returns an array of `ModuleResource` objects. When `expand=descendants` is used, each object includes a `children` array recursively.

```json
[
  {
    "id": 2107600,
    "name": "Authentication",
    "pid": "MD-1",
    "parent_id": null,
    "order": 1,
    "shared": false,
    "children": [
      {
        "id": 2107619,
        "name": "Login",
        "pid": "MD-8",
        "parent_id": 2107600,
        "order": 1,
        "shared": false,
        "children": []
      },
      {
        "id": 2107620,
        "name": "Logout",
        "pid": "MD-9",
        "parent_id": 2107600,
        "order": 2,
        "shared": false,
        "children": []
      }
    ]
  },
  {
    "id": 2107650,
    "name": "Payment",
    "pid": "MD-2",
    "parent_id": null,
    "order": 2,
    "shared": false,
    "children": []
  }
]
```

### `ModuleResource` Schema

| Field | Type | Description |
|---|---|---|
| `id` | integer (int64) | Primary numeric identifier — use this as `parent_id` when creating test cases |
| `name` | string | Display name of the module |
| `pid` | string | Human-readable identifier (e.g., `"MD-8"`) |
| `parent_id` | integer \| null | `id` of the parent module; `null` for root modules |
| `order` | integer | Display order within its parent |
| `shared` | boolean | Whether the module is shared across projects |
| `children` | array of `ModuleResource` | Nested child modules (only present with `?expand=descendants`) |

---

## 2. Get a Single Module

Retrieve a specific module by its numeric ID.

### Endpoint

```
GET /api/v3/projects/{projectId}/modules/{moduleId}
```

### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `projectId` | integer (int64) | Yes | Numeric ID of the qTest project |
| `moduleId` | integer (int64) | Yes | Numeric ID of the module to retrieve |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `expand` | string | No | Pass `"descendants"` to include the subtree rooted at this module |

### Request Example

```http
GET https://mycompany.qtestnet.com/api/v3/projects/12345/modules/2107619
Authorization: Bearer {access_token}
```

### Response — `200 OK`

```json
{
  "id": 2107619,
  "name": "Login",
  "pid": "MD-8",
  "parent_id": 2107600,
  "order": 1,
  "shared": false,
  "children": []
}
```

---

## 3. Create a Module

Create a new folder inside a project. Use `parentId` to nest it inside an existing module.

### Endpoint

```
POST /api/v3/projects/{projectId}/modules
```

### Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `projectId` | integer (int64) | Yes | Numeric ID of the qTest project |

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `parentId` | integer (int64) | No | Place the new module inside this parent. Omit to create at root level. |

### Request Body — `ModuleResource`

```json
{
  "name": "My New Folder",
  "shared": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Name for the new module/folder |
| `shared` | boolean | No | Whether this module should be shared. Defaults to `false`. |
| `description` | string | No | Optional description for the module |

### Request Example

```http
POST https://mycompany.qtestnet.com/api/v3/projects/12345/modules?parentId=2107600
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Password Reset",
  "shared": false
}
```

### Response — `200 OK`

```json
{
  "id": 2107700,
  "name": "Password Reset",
  "pid": "MD-15",
  "parent_id": 2107600,
  "order": 3,
  "shared": false,
  "children": []
}
```

---

## 4. Update or Move a Module

Rename or move a module to a different parent.

### Endpoint

```
PUT /api/v3/projects/{projectId}/modules/{moduleId}
```

### Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `parentId` | integer (int64) | No | When provided, **moves** the module to this new parent. The request body is ignored in move mode. |

### Request Example (rename)

```http
PUT https://mycompany.qtestnet.com/api/v3/projects/12345/modules/2107700
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Forgot Password"
}
```

### Request Example (move)

```http
PUT https://mycompany.qtestnet.com/api/v3/projects/12345/modules/2107700?parentId=2107650
Authorization: Bearer {access_token}
Content-Type: application/json

{}
```

---

## 5. Delete a Module

```
DELETE /api/v3/projects/{projectId}/modules/{moduleId}
```

| Query Param | Type | Description |
|---|---|---|
| `force` | boolean | Pass `true` to delete the module and all its children. Omit to fail if the module has children. |

---

## Common Error Responses

| Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid `parentId` or malformed request body |
| `401 Unauthorized` | Missing or expired Bearer token |
| `403 Forbidden` | Authenticated user does not have access to this project |
| `404 Not Found` | `projectId` or `moduleId` does not exist |

---

## Usage Pattern

To find the ID of a target folder before creating test cases:

```bash
# Step 1: Get the full module tree
curl -s -X GET \
  "https://mycompany.qtestnet.com/api/v3/projects/12345/modules?expand=descendants" \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.[] | {id, name, pid}'
```

Capture the `id` value for your target folder, then use it as `parent_id` when calling the test case creation endpoints described in the next documents.
