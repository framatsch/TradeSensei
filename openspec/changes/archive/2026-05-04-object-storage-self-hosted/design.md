## Context

The backend's `StorageService` uses `boto3` with a configurable `endpoint_url` — this
is the S3-compatible API that every major object storage provider supports. The six
`STORAGE_*` env vars (`STORAGE_BACKEND`, `STORAGE_BUCKET`, `STORAGE_PUBLIC_URL`,
`STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_ENDPOINT_URL`) are all that need
to change between providers. No backend code changes are required for any provider.

**Supported providers out of the box (no code changes needed):**

| Provider              | endpoint_url                          | Notes                               |
| --------------------- | ------------------------------------- | ----------------------------------- |
| AWS S3                | _(leave empty)_                       | default boto3 behaviour             |
| Cloudflare R2         | `https://<account>.r2.cloudflarestorage.com` | no egress fees                |
| Hetzner Object Storage| `https://<region>.your-objectstorage.com`    | EU-hosted                     |
| Backblaze B2          | `https://s3.<region>.backblazeb2.com` | cheapest per-GB                     |
| SeaweedFS (S3 mode)   | `http://seaweedfs:8333`               | self-hosted, bundled in Compose     |

## Goals / Non-Goals

**Goals:**
- Provide a zero-config self-hosted storage option via SeaweedFS in Docker Compose
- Document all provider options clearly in `docs/dev-guide.md`
- Fix `docker-compose.prod.yml` which is missing all `STORAGE_*` vars

**Non-Goals:**
- Changing the upload API or storage_service.py
- Supporting non-S3 protocols (GCS native, Azure Blob, etc.)
- Automatic bucket creation for cloud providers (user must create bucket manually)

## Decisions

### D1: SeaweedFS over MinIO for self-hosted bundled storage

**Decision:** Use SeaweedFS (`chrislusf/seaweedfs`) as the bundled self-hosted option.

**Alternatives considered:**
- MinIO: widely used, S3-compatible, but AGPL-licensed which can be a concern for
  self-hosters running modified versions. Also heavier in memory footprint.
- SeaweedFS: Apache 2.0 licensed, lighter weight, S3-compatible gateway mode (`weed s3`),
  presigned URL support confirmed. Suitable for a bundled single-node deployment.

**Rationale:** User explicitly requested SeaweedFS. Both work identically with boto3.

### D2: Docker Compose `storage` profile — opt-in, not default

**Decision:** The SeaweedFS service is gated behind a Docker Compose profile named
`storage`. Users who have external S3 (AWS, R2, etc.) do not start an unnecessary
local service. The dev stack starts normally without it.

**Usage:**
```bash
# With bundled storage
docker compose --profile storage up -d

# Without (external provider configured via env)
docker compose up -d
```

### D3: Bucket initialisation via an init container

**Decision:** Add a one-shot `storage-init` service that depends on SeaweedFS being
healthy, creates the `tradesensei` bucket, and sets a public-read bucket policy so
that the `public_url` pattern `http://seaweedfs:8333/tradesensei/<key>` works without
credentials. Uses the `amazon/aws-cli` image with `AWS_EC2_METADATA_DISABLED=true`.

**Rationale:** SeaweedFS does not auto-create buckets. Without this, the first upload
fails with a "NoSuchBucket" error.

### D4: `STORAGE_PUBLIC_URL` for SeaweedFS points to Nginx (prod) or localhost (dev)

**Decision:**
- Dev: `STORAGE_PUBLIC_URL=http://localhost:8333/tradesensei` (direct SeaweedFS port)
- Prod: `STORAGE_PUBLIC_URL=https://<your-domain>/storage/tradesensei` — requires Nginx
  to proxy `/storage/` → SeaweedFS. Add a Nginx location block for this.

**Rationale:** In prod, SeaweedFS should not be directly exposed. Nginx proxies it under
the same domain, keeping the deployment behind a single TLS termination point.

## Risks / Trade-offs

- **[Risk] SeaweedFS presigned URL hostname in containers** — presigned URLs are
  generated with the internal `http://seaweedfs:8333` host. The browser cannot reach
  this host. Mitigation: `STORAGE_PUBLIC_URL` must be set to the externally reachable
  URL (localhost in dev, domain in prod). The presigned PUT goes to the internal host
  (backend calls it server-side via the init flow) — wait, **the frontend uploads
  directly to the presigned URL**. This means the presigned URL hostname must be
  reachable from the browser.
  → **Dev mitigation**: expose SeaweedFS port 8333 to host, use `http://localhost:8333`
    as both `STORAGE_ENDPOINT_URL` and `STORAGE_PUBLIC_URL` base.
  → **Prod mitigation**: expose SeaweedFS via Nginx proxy, use the public domain.

- **[Risk] SeaweedFS data persistence** — SeaweedFS stores data in a volume. If the
  volume is deleted (`docker compose down -v`), all uploads are lost. This is expected
  and documented — same as the database volume.

## Open Questions

- Should the Nginx prod config snippet be added to the existing `nginx/nginx.conf` or
  provided as a separate example? (Assumption: add as a commented block in docs)
