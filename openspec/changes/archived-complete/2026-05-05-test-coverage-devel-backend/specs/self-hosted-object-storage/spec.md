## ADDED Requirements

### Requirement: StorageService is unit-testable without a real S3 endpoint
The implementation SHALL expose the boto3 client as a cached property that can be patched in tests without network calls.

#### Scenario: boto3 client can be patched in unit tests
- **WHEN** `boto3.client` is patched before `StorageService._s3_client` is first accessed
- **THEN** the patched mock is used for all `generate_presigned_url` calls

### Requirement: Presigned upload URL endpoint delegates to StorageService
The screenshot presigned-URL API endpoint SHALL call `StorageService.generate_screenshot_upload_url` and return the URL to the client.

#### Scenario: POST to presigned-upload endpoint returns URL
- **WHEN** an authenticated owner POSTs to the presigned screenshot upload endpoint with a valid filename and content_type
- **THEN** the response contains a `upload_url` and `public_url` field
