## ADDED Requirements

### Requirement: Generate presigned upload URL for playbook image
The system SHALL provide an endpoint to generate a presigned PUT URL for uploading an image to a playbook.

#### Scenario: Successful URL generation for PNG
- **WHEN** an authenticated user requests an upload URL for a playbook they own, with `content_type = image/png`
- **THEN** the system returns 200 with an `upload_url` (presigned PUT) and `public_url` (read URL)

#### Scenario: Successful URL generation for JPEG
- **WHEN** an authenticated user requests an upload URL with `content_type = image/jpeg`
- **THEN** the system returns 200 with a presigned URL

#### Scenario: Successful URL generation for WebP
- **WHEN** an authenticated user requests an upload URL with `content_type = image/webp`
- **THEN** the system returns 200 with a presigned URL

#### Scenario: Non-image content type rejected
- **WHEN** an authenticated user requests an upload URL with `content_type = application/pdf`
- **THEN** the system returns 422 Unprocessable Entity

#### Scenario: Unsupported content type rejected
- **WHEN** an authenticated user requests an upload URL with `content_type = text/plain`
- **THEN** the system returns 422 Unprocessable Entity

#### Scenario: Storage not configured
- **WHEN** `STORAGE_PUBLIC_URL` is empty or absent
- **THEN** the system returns 503 Service Unavailable

#### Scenario: Playbook not owned by user
- **WHEN** the request targets a playbook not owned by the authenticated user
- **THEN** the system returns 404

### Requirement: Register uploaded image on playbook
The system SHALL allow registering a previously uploaded image as an attachment on a playbook.

#### Scenario: Successful registration
- **WHEN** a POST request provides a `filename`, `content_type` (image/*), and `storage_url` matching the `STORAGE_PUBLIC_URL` prefix for an owned playbook
- **THEN** the system creates a `playbook_attachments` row and returns 201 with `id`, `filename`, `content_type`, `storage_url`, `created_at`

#### Scenario: Untrusted URL rejected
- **WHEN** a POST request provides a `storage_url` that does not match the configured `STORAGE_PUBLIC_URL` prefix
- **THEN** the system returns 422

### Requirement: List images for playbook
The system SHALL return all images registered on a playbook.

#### Scenario: Returns image list
- **WHEN** a GET request is sent for images of an owned playbook
- **THEN** the system returns 200 with a list of `id`, `filename`, `content_type`, `storage_url`, `created_at`

#### Scenario: Returns empty list when no images
- **WHEN** a GET request is sent for a playbook with no images
- **THEN** the system returns 200 with an empty list

### Requirement: Delete playbook image
The system SHALL allow deleting an image from a playbook.

#### Scenario: Successful deletion
- **WHEN** a DELETE request targets an existing image on an owned playbook
- **THEN** the attachment row is removed and the system returns 204

#### Scenario: Image not found returns 404
- **WHEN** a DELETE request targets an attachment ID that does not exist on the playbook
- **THEN** the system returns 404

#### Scenario: Images cascade-deleted on playbook delete
- **WHEN** a playbook is deleted
- **THEN** all `playbook_attachments` rows for that playbook are removed (CASCADE)
