## Why

The application supports screenshot and trade image uploads via a presigned S3-compatible
upload flow, but the Docker deployment stack has no object storage service. Users who
self-host without a pre-existing cloud storage provider (AWS S3, Cloudflare R2, etc.)
cannot use image uploads at all — all upload endpoints return HTTP 503. The `STORAGE_*`
environment variables exist but are undocumented and have no working default for local
or self-hosted deployments. This needs to be solved at the infrastructure layer with a
bundled storage option and clear documentation for all provider alternatives.

## What Changes

- **ADD** SeaweedFS service to `docker-compose.yml` (local dev, opt-in via Docker profile `storage`)
- **ADD** SeaweedFS service to `docker-compose.prod.yml` (self-hosted prod, opt-in via profile `storage`)
- **ADD** SeaweedFS bucket/policy init container that creates the `tradesensei` bucket and sets public-read ACL on startup
- **ADD** `STORAGE_*` environment variables to `docker-compose.prod.yml` backend service (currently missing entirely)
- **UPDATE** `docs/dev-guide.md` — document all supported storage providers with copy-paste config snippets: SeaweedFS (self-hosted), AWS S3, Cloudflare R2, Hetzner Object Storage, Backblaze B2
- **UPDATE** `docker-compose.yml` comments — replace the existing MinIO example with a SeaweedFS example

## Capabilities

### New Capabilities

- `self-hosted-object-storage`: SeaweedFS bundled in Docker Compose as an opt-in profile, zero-config for self-hosters; documented config for all major S3-compatible cloud providers

### Modified Capabilities

- (none — no spec-level behaviour changes; the upload flow itself is unchanged)

## Impact

- **Files modified:** `docker-compose.yml`, `docker-compose.prod.yml`, `docs/dev-guide.md`
- **No backend changes** — `storage_service.py` already works with any S3-compatible endpoint
- **No frontend changes** — upload flow is provider-agnostic
- **Optional / non-breaking** — storage profile is opt-in; deployments without it continue to get HTTP 503 (existing behaviour, now documented)
