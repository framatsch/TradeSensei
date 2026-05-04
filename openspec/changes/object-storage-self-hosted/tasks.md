## 1. docker-compose.yml — SeaweedFS service + init container

- [x] 1.1 Add `seaweedfs` service under the `storage` profile — image `chrislusf/seaweedfs`, command `server -s3 -s3.port=8333 -dir=/data`, port `8333:8333` exposed to host, volume `seaweedfs_data:/data`, healthcheck on `http://localhost:8333/`
- [x] 1.2 Add `storage-init` service under the `storage` profile — image `amazon/aws-cli`, depends on `seaweedfs` healthy, one-shot command that creates the `tradesensei` bucket and sets public-read policy via `aws s3api` with `AWS_EC2_METADATA_DISABLED=true` and `--endpoint-url http://seaweedfs:8333`
- [x] 1.3 Set `restart: on-failure` on `storage-init` so it retries if SeaweedFS isn't ready yet, then exits with code 0 on success
- [x] 1.4 Add `seaweedfs_data` to the top-level `volumes:` block
- [x] 1.5 Update the `STORAGE_*` comment block in the backend service to use SeaweedFS example values instead of the current MinIO example:
  ```
  STORAGE_BACKEND=s3
  STORAGE_BUCKET=tradesensei
  STORAGE_PUBLIC_URL=http://localhost:8333/tradesensei
  STORAGE_ACCESS_KEY=any
  STORAGE_SECRET_KEY=any
  STORAGE_ENDPOINT_URL=http://seaweedfs:8333
  ```
- [x] 1.6 Add a comment noting that `STORAGE_ENDPOINT_URL` must use the **host-reachable** address in the `STORAGE_PUBLIC_URL` (i.e. `localhost:8333`, not `seaweedfs:8333`) so presigned URLs work from the browser

## 2. docker-compose.prod.yml — STORAGE_* stubs + SeaweedFS profile

- [x] 2.1 Add all six `STORAGE_*` env vars to the `backend` service in `docker-compose.prod.yml` as commented stubs with provider examples in the comment
- [x] 2.2 Add `seaweedfs` service under the `storage` profile in `docker-compose.prod.yml` — same image as dev but **without** host port exposure (internal network only), volume `seaweedfs_data:/data`
- [x] 2.3 Add `storage-init` service under the `storage` profile in `docker-compose.prod.yml` — same init pattern as dev, endpoint `http://seaweedfs:8333`
- [x] 2.4 Add a Nginx location block comment in `docker-compose.prod.yml` (or a reference to the docs) explaining that `/storage/` must be proxied to `http://seaweedfs:8333` for browser-accessible presigned URLs
- [x] 2.5 Add `seaweedfs_data` to the `volumes:` block in `docker-compose.prod.yml`

## 3. docs/dev-guide.md — Object Storage section

- [x] 3.1 Add an "## Object Storage" section to `docs/dev-guide.md` explaining the optional upload feature and the `STORAGE_*` env var model
- [x] 3.2 Add subsection "### Option 1: SeaweedFS (self-hosted, bundled)" with the exact `docker compose --profile storage up -d` command and the env var values to set
- [x] 3.3 Add subsection "### Option 2: AWS S3" with bucket creation steps and the exact env vars (no `STORAGE_ENDPOINT_URL` needed)
- [x] 3.4 Add subsection "### Option 3: Cloudflare R2" with R2 dashboard steps (create bucket, create API token with R2 permissions) and env vars including the R2 endpoint URL format
- [x] 3.5 Add subsection "### Option 4: Hetzner Object Storage" with the endpoint URL pattern and env vars
- [x] 3.6 Add subsection "### Option 5: Backblaze B2" with the S3-compatible endpoint and env vars
- [x] 3.7 Add a "### Disabling uploads" note explaining that leaving `STORAGE_BACKEND` empty disables uploads gracefully (HTTP 503), which is the default

## 4. Verification

- [x] 4.1 Run `docker compose --profile storage up -d` locally — verify SeaweedFS starts and `storage-init` exits with code 0
- [x] 4.2 Verify the `tradesensei` bucket exists: `aws s3 ls --endpoint-url http://localhost:8333 s3://tradesensei`
- [x] 4.3 Set the `STORAGE_*` env vars in the backend to the SeaweedFS dev values and upload a test screenshot via the API — verify presigned URL is browser-reachable and the image is accessible at `http://localhost:8333/tradesensei/<key>`
- [x] 4.4 Verify `docker compose up -d` (without `--profile storage`) starts cleanly with no errors related to storage
