## ADDED Requirements

### Requirement: Self-hosted deployments can enable bundled object storage via a Docker Compose profile
The Docker Compose stack SHALL provide an optional `storage` profile that starts a SeaweedFS service as an S3-compatible object store. When the `storage` profile is active, the `tradesensei` bucket SHALL be automatically created on first startup. The profile SHALL be opt-in so deployments using external providers (AWS S3, Cloudflare R2, etc.) are unaffected.

#### Scenario: Starting with bundled storage
- **WHEN** the user runs `docker compose --profile storage up -d`
- **THEN** a SeaweedFS container starts alongside the backend and frontend
- **AND** a `tradesensei` bucket is created automatically if it does not exist
- **AND** the backend is able to generate presigned PUT URLs against the local SeaweedFS endpoint

#### Scenario: Starting without bundled storage
- **WHEN** the user runs `docker compose up -d` (no `--profile storage`)
- **THEN** no SeaweedFS container is started
- **AND** the stack behaves identically to the current behaviour
- **AND** upload endpoints return HTTP 503 if no `STORAGE_*` env vars are configured

#### Scenario: SeaweedFS persists uploads across restarts
- **WHEN** the Docker Compose stack is stopped and restarted (without `-v`)
- **THEN** previously uploaded images remain accessible at their public URLs

### Requirement: Production docker-compose includes all STORAGE_* environment variable stubs
The `docker-compose.prod.yml` backend service SHALL include all six `STORAGE_*` environment variables as commented stubs with clear documentation of their purpose. This enables operators to configure any S3-compatible provider by setting these variables.

#### Scenario: Operator configures Cloudflare R2
- **WHEN** the operator sets `STORAGE_BACKEND=s3`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_ENDPOINT_URL` (R2 endpoint), and `STORAGE_PUBLIC_URL`
- **THEN** the backend generates valid presigned PUT URLs for R2
- **AND** uploaded files are stored in the R2 bucket

#### Scenario: Operator configures AWS S3
- **WHEN** the operator sets `STORAGE_BACKEND=s3`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, and `STORAGE_PUBLIC_URL` (with `STORAGE_ENDPOINT_URL` left empty)
- **THEN** the backend uses the default boto3 AWS S3 endpoint

### Requirement: Documentation covers all supported storage providers with copy-paste config
The developer guide (`docs/dev-guide.md`) SHALL contain a dedicated "Object Storage" section documenting how to configure uploads for each supported provider. Each provider entry SHALL include the exact environment variable values needed.

#### Scenario: Developer sets up local storage for development
- **WHEN** a developer follows the SeaweedFS setup instructions in the dev guide
- **THEN** they can upload screenshots and trade images in their local environment within 5 minutes

#### Scenario: Self-hoster chooses Cloudflare R2
- **WHEN** a self-hoster follows the R2 setup instructions
- **THEN** they have the exact `STORAGE_*` values to set without needing to read boto3 or R2 documentation

### Requirement: Browser-reachable presigned URLs in all deployment modes
The `STORAGE_PUBLIC_URL` and `STORAGE_ENDPOINT_URL` configuration SHALL be documented with clear guidance on the hostname visibility problem. In self-hosted deployments, the presigned URL host MUST be reachable from the user's browser (not just from inside Docker's internal network).

#### Scenario: Dev — SeaweedFS reachable from browser
- **WHEN** SeaweedFS is running via Docker Compose with port 8333 exposed to the host
- **THEN** the browser can PUT directly to `http://localhost:8333/...` using the presigned URL

#### Scenario: Prod — SeaweedFS behind Nginx proxy
- **WHEN** SeaweedFS is proxied via Nginx at `/storage/`
- **THEN** the browser can PUT to `https://<domain>/storage/...` using the presigned URL
- **AND** SeaweedFS port is NOT directly exposed to the public internet
