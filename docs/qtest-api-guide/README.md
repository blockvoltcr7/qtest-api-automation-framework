# qTest Manager API — Developer Guide

This guide covers the qTest Manager v3 REST API for managing test cases and module folders within a project. It is intended for engineers building automation pipelines that create, organize, or populate test cases programmatically.

## Contents

| Document | Description |
|---|---|
| [01-authentication.md](./01-authentication.md) | How to obtain and use a Bearer token |
| [02-modules-api.md](./02-modules-api.md) | Retrieve module (folder) IDs from the project tree |
| [03-create-single-test-case.md](./03-create-single-test-case.md) | Create one test case inside a module |
| [04-create-bulk-test-cases.md](./04-create-bulk-test-cases.md) | Create a collection of test cases via automation test logs |

## Base URL

All endpoints use the following base URL pattern:

```
https://{your-qtest-domain}/api/v3
```

Replace `{your-qtest-domain}` with your organization's qTest hostname (e.g., `mycompany.qtestnet.com`).

## Common Headers

Every request must include these headers:

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

## Workflow Overview

The typical flow for populating test cases into a specific module folder is:

```
1. Authenticate → obtain Bearer token
        |
        v
2. GET /projects/{projectId}/modules?expand=descendants
        → find target module numeric ID
        |
        v
3a. POST /projects/{projectId}/test-cases          (single test case)
        |
        OR
        |
3b. POST /projects/{projectId}/auto-test-logs      (collection of test cases)
        |
        v
4. (Bulk only) Poll /projects/queue-processing/{jobId} until complete
```

## API Reference Links

- Swagger UI: `https://qtest.dev.tricentis.com/`
- OpenAPI Spec (YAML): `https://qtest-config.s3.amazonaws.com/api-docs/manager/api-manager-v3.0.yaml`
- Tricentis Docs: `https://documentation.tricentis.com/qtest/od/en/content/apis/overview/qtest_api_specification.htm`
