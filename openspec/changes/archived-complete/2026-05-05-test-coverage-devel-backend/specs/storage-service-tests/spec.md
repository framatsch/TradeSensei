## ADDED Requirements

### Requirement: StorageService generates a presigned upload URL for allowed content types
The system SHALL call `boto3.client.generate_presigned_url` and return a tuple of `(presigned_url, object_key)` for `image/png`, `image/jpeg`, and `image/webp`.

#### Scenario: PNG content type returns presigned URL
- **WHEN** `StorageService._generate_upload_url` is called with `content_type="image/png"` and storage is configured
- **THEN** a presigned PUT URL and object key are returned

#### Scenario: Presigned URL includes correct S3 parameters
- **WHEN** `StorageService._generate_upload_url` is called with valid inputs
- **THEN** `boto3_client.generate_presigned_url` is called with `ClientMethod="put_object"` and the correct `Bucket` and `Key`

### Requirement: StorageService rejects disallowed content types
The system SHALL raise `UnsupportedContentTypeError` for any content type not in the allowed set.

#### Scenario: Disallowed content type raises error
- **WHEN** `StorageService._generate_upload_url` is called with `content_type="application/pdf"`
- **THEN** `UnsupportedContentTypeError` is raised

### Requirement: StorageService raises ConfigurationError when storage is not configured
The system SHALL raise `ConfigurationError` when `settings.storage_backend` is falsy.

#### Scenario: Missing storage config raises error
- **WHEN** `StorageService._generate_upload_url` is called and `settings.storage_backend` is not set
- **THEN** `ConfigurationError` is raised

### Requirement: StorageService rejects empty filename
The system SHALL raise a `ValueError` when an empty or path-traversal filename is provided.

#### Scenario: Empty filename raises ValueError
- **WHEN** `StorageService._generate_upload_url` is called with an empty `filename`
- **THEN** `ValueError` is raised
