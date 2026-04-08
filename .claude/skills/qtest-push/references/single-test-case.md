# Single Test Case API Reference

## Endpoint

```
POST /api/v3/projects/{projectId}/test-cases
```

## Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `parentId` | integer | No | Module ID. Takes precedence over `parent_id` in body. Omit → placed in "Created via API" default folder. |

## Request Body Schema

```json
{
  "name": "string",
  "parent_id": 0,
  "description": "string (HTML allowed)",
  "precondition": "string (HTML allowed)",
  "order": 0,
  "creator_id": 0,
  "properties": [
    {
      "field_id": 0,
      "field_value": "string",
      "field_value_name": "string"
    }
  ],
  "test_steps": [
    {
      "description": "string",
      "expected": "string",
      "order": 1,
      "called_test_case": { "id": 0, "approved": true }
    }
  ]
}
```

### Required Fields

| Field | Notes |
|---|---|
| `name` | Display name of the test case |
| `properties` | Array of custom field values. Pass `[]` if none required. |

### Optional Fields

| Field | Notes |
|---|---|
| `parent_id` | Integer module ID. Determines folder placement. |
| `description` | HTML-formatted test case description |
| `precondition` | HTML-formatted precondition |
| `order` | Display order within the module (lower = first) |
| `test_steps` | Array of step objects. Each needs `description`, `expected`, `order`. |

## Success Response — 201 Created

```json
{
  "id": 9876543,
  "pid": "TC-412",
  "name": "...",
  "parent_id": 2107619,
  "status": "UNAPPROVED",
  "version": 1,
  "web_url": "https://mycompany.qtestnet.com/p/12345/portal/project#tab=testdesign&object=1&id=9876543",
  "created_date": "2026-04-08T10:00:00.000Z"
}
```

## Error Codes

| Code | Cause |
|---|---|
| 400 | Missing `name`/`properties`, invalid `parent_id`, malformed JSON |
| 401 | Expired or missing Bearer token |
| 403 | No project access |
| 404 | `projectId` or module ID not found |
