# Create a Single Test Case

Use this endpoint to create one test case and place it inside a specific module (folder) in qTest Manager's Test Design tree.

---

## Endpoint

```
POST /api/v3/projects/{projectId}/test-cases
```

**Full URL:**
```
https://{your-qtest-domain}/api/v3/projects/{projectId}/test-cases
```

---

## Path Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `projectId` | integer (int64) | Yes | The numeric ID of the qTest project where the test case will be created |

---

## Query Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `parentId` | integer (int64) | No | The numeric `id` of the module (folder) to place the test case in. Takes precedence over `parent_id` in the request body if both are provided. If neither is provided, the test case is placed in the auto-generated **"Created via API"** module. |

---

## Request Headers

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## Request Body Schema — `TestCaseWithCustomFieldResource`

```json
{
  "name": "string",
  "parent_id": 0,
  "description": "string",
  "precondition": "string",
  "order": 0,
  "creator_id": 0,
  "agent_ids": [0],
  "properties": [
    {
      "field_id": 0,
      "field_value": "string",
      "field_value_name": "string"
    }
  ],
  "test_steps": [
    {
      "id": 0,
      "description": "string",
      "expected": "string",
      "order": 0,
      "called_test_case": {
        "id": 0,
        "approved": true
      }
    }
  ]
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | **Yes** | The display name of the test case |
| `properties` | array of `PropertyResource` | **Yes** | Custom field values. Must include all fields marked as required in the project's field configuration. Pass an empty array `[]` if no custom fields are required. |
| `parent_id` | integer (int64) | No | The numeric `id` of the target module (folder). Determines where the test case lives in the Test Design tree. Overridden by the `parentId` query parameter if both are provided. |
| `description` | string | No | HTML-formatted description of the test case |
| `precondition` | string | No | HTML-formatted precondition text |
| `order` | integer | No | Display order of this test case within its parent module. Lower numbers appear first. |
| `creator_id` | integer (int64) | No | User ID to attribute as creator. Defaults to the authenticated user. |
| `agent_ids` | array of integers | No | IDs of qTest automation agents associated with this test case |

---

### `PropertyResource` — Custom Field Values

Each object in the `properties` array sets the value of one custom field on the test case.

```json
{
  "field_id": 101,
  "field_value": "High",
  "field_value_name": "High Priority"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `field_id` | integer (int64) | Yes | The numeric ID of the custom field. Retrieve field IDs from the project's field configuration API. |
| `field_value` | string | Yes | The value to assign. For list/dropdown fields, this is typically the option ID or code. For text fields, this is the raw string. |
| `field_value_name` | string | No | The human-readable label for the value (used for list fields). Informational only — `field_value` is the authoritative value. |

---

### `TestStepResource` — Test Steps

Each object in the `test_steps` array defines one step in the test case. Steps are executed in the order defined by the `order` field.

```json
{
  "description": "Navigate to the login page",
  "expected": "The login form is displayed",
  "order": 1
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | string | Yes | The action or instruction for this step (what the tester does) |
| `expected` | string | Yes | The expected result after performing this step |
| `order` | integer | Yes | Step sequence number. Steps are displayed in ascending order. Must be unique within the test case. |
| `id` | integer (int64) | No | Only required when **updating** an existing step. Omit for new steps. |
| `called_test_case` | object | No | Used for "call test case" steps — embeds another test case as a reusable step. See below. |

#### `called_test_case` Object

| Field | Type | Description |
|---|---|---|
| `id` | integer (int64) | The `id` of the test case being called |
| `approved` | boolean | Whether to use the approved version of the called test case |

---

## Full Request Example

### Minimal (required fields only)

```http
POST https://mycompany.qtestnet.com/api/v3/projects/12345/test-cases?parentId=2107619
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "name": "Verify login with valid credentials",
  "properties": []
}
```

### Complete Example

```http
POST https://mycompany.qtestnet.com/api/v3/projects/12345/test-cases?parentId=2107619
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
Content-Type: application/json

{
  "name": "Verify login with valid credentials",
  "parent_id": 2107619,
  "description": "<p>Validates that a registered user can authenticate using a valid username and password combination.</p>",
  "precondition": "<p>The user has an active account with known credentials.</p>",
  "order": 1,
  "properties": [
    {
      "field_id": 101,
      "field_value": "2",
      "field_value_name": "High"
    },
    {
      "field_id": 102,
      "field_value": "Regression",
      "field_value_name": "Regression"
    }
  ],
  "test_steps": [
    {
      "description": "Open the application URL in a browser",
      "expected": "The home page loads and the Login button is visible",
      "order": 1
    },
    {
      "description": "Click the Login button",
      "expected": "The login page is displayed with username and password fields",
      "order": 2
    },
    {
      "description": "Enter a valid username into the Username field",
      "expected": "The username is accepted without error",
      "order": 3
    },
    {
      "description": "Enter the corresponding valid password into the Password field",
      "expected": "The password is masked and accepted",
      "order": 4
    },
    {
      "description": "Click the Submit button",
      "expected": "The user is redirected to the dashboard and a welcome message is displayed",
      "order": 5
    }
  ]
}
```

---

## Response

### Success — `201 Created`

Returns the full created test case object with server-assigned fields populated.

```json
{
  "id": 9876543,
  "pid": "TC-412",
  "name": "Verify login with valid credentials",
  "parent_id": 2107619,
  "description": "<p>Validates that a registered user can authenticate...</p>",
  "precondition": "<p>The user has an active account with known credentials.</p>",
  "order": 1,
  "status": "UNAPPROVED",
  "version": 1,
  "web_url": "https://mycompany.qtestnet.com/p/12345/portal/project#tab=testdesign&object=1&id=9876543",
  "creator": {
    "id": 555,
    "username": "user@example.com"
  },
  "created_date": "2026-04-08T10:00:00.000Z",
  "last_modified_date": "2026-04-08T10:00:00.000Z",
  "properties": [
    {
      "field_id": 101,
      "field_value": "2",
      "field_value_name": "High"
    }
  ],
  "test_steps": [
    {
      "id": 11001,
      "description": "Open the application URL in a browser",
      "expected": "The home page loads and the Login button is visible",
      "order": 1
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|---|---|---|
| `id` | integer (int64) | Server-assigned numeric ID — use this to reference the test case in future API calls |
| `pid` | string | Human-readable project-scoped ID (e.g., `"TC-412"`) — shown in the qTest UI |
| `name` | string | Test case name |
| `parent_id` | integer (int64) | The module (folder) this test case was placed in |
| `status` | string | Approval status: `"UNAPPROVED"`, `"APPROVED"` |
| `version` | integer | Version number (starts at `1`) |
| `web_url` | string | Direct link to open this test case in the qTest Manager UI |
| `created_date` | string (ISO 8601) | Timestamp when the test case was created |
| `last_modified_date` | string (ISO 8601) | Timestamp of last modification |
| `creator` | object | User who created the test case (`id` and `username`) |

---

## Error Responses

| Status | Cause | Resolution |
|---|---|---|
| `400 Bad Request` | Missing required fields (`name` or `properties`), invalid `parent_id`, or malformed JSON | Check the request body matches the schema |
| `401 Unauthorized` | Missing or expired Bearer token | Re-authenticate and use a fresh token |
| `403 Forbidden` | Authenticated user lacks permission to create test cases in this project | Verify project membership and role |
| `404 Not Found` | `projectId` or `parentId`/`parent_id` module does not exist | Confirm project and module IDs using the Modules API |
| `413 Payload Too Large` | Request body exceeds size limits | Reduce the number of test steps or field values |

---

## Notes

- **Module placement priority:** If you provide both the `parentId` query parameter and `parent_id` in the body, the query parameter takes precedence.
- **Default module:** If neither is provided, the test case is placed in a system-generated module named **"Created via API"**. This is rarely desired — always specify a `parentId`.
- **Custom field IDs:** Retrieve the list of available custom fields and their IDs using: `GET /api/v3/projects/{projectId}/settings/test-cases/fields`
- **Test case status:** New test cases always start as `"UNAPPROVED"`. Use the approval workflow API to change this.
- **Updating an existing test case:** Use `PUT /api/v3/projects/{projectId}/test-cases/{testCaseId}` with the same body schema. Include `id` on each existing test step to update it rather than create a duplicate.

---

## curl Example

```bash
curl -s -X POST \
  "https://mycompany.qtestnet.com/api/v3/projects/12345/test-cases?parentId=2107619" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Verify login with valid credentials",
    "parent_id": 2107619,
    "properties": [],
    "test_steps": [
      {
        "description": "Navigate to login page",
        "expected": "Login form is displayed",
        "order": 1
      }
    ]
  }' | jq '{id, pid, name, parent_id, web_url}'
```
