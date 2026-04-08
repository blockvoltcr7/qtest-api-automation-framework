# Single Test Case — Full API Schema

## Endpoint

```
POST /api/v3/projects/{projectId}/test-cases
```

## Query Parameters

| Param | Type | Notes |
|---|---|---|
| `parentId` | integer | Module ID. Takes precedence over `parent_id` in body. Omit → placed in "Created via API" default folder. |

## Request Body

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
| `properties` | Custom field values array. Pass `[]` if none required. |

### Optional Fields

| Field | Notes |
|---|---|
| `parent_id` | Integer module ID for folder placement |
| `description` | HTML-formatted test case description |
| `precondition` | HTML-formatted precondition text |
| `order` | Display order within the module (lower = first) |
| `test_steps` | Array — each step needs `description`, `expected`, `order` |

## Success Response — 201 Created

```json
{
  "id": 9876543,
  "pid": "TC-412",
  "name": "Verify login with valid credentials",
  "parent_id": 2107619,
  "status": "UNAPPROVED",
  "version": 1,
  "web_url": "https://mycompany.qtestnet.com/p/12345/portal/project#tab=testdesign&object=1&id=9876543",
  "created_date": "2026-04-08T10:00:00.000Z"
}
```

## Minimal curl Example

```bash
curl -s -X POST \
  "${QTEST_BASE_URL}/api/v3/projects/${QTEST_PROJECT_ID}/test-cases?parentId=${MODULE_ID}" \
  -H "Authorization: Bearer ${QTEST_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Verify login with valid credentials",
    "parent_id": 2107619,
    "properties": [],
    "test_steps": [
      { "description": "Navigate to login page", "expected": "Login form displayed", "order": 1 },
      { "description": "Submit valid credentials", "expected": "Redirected to dashboard", "order": 2 }
    ]
  }'
```
