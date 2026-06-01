## Context

The Trade Sensei platform stores uploaded images (trade screenshots, daily checkin screenshots, playbook attachments) in SeaweedFS S3-compatible storage. Currently, the database stores full public URLs and SeaweedFS is configured with anonymous read access, meaning anyone with a URL can view images indefinitely without authentication.

This is a security risk because trade screenshots contain sensitive P&L data and positions. A leaked URL (browser history, shared screenshot, referrer header) exposes this data permanently.

**Current Flow:**
1. Client requests upload URL via `POST /checkins/upload-url`
2. Backend generates presigned PUT URL and constructs public GET URL
3. Backend stores public URL in database (`screenshot_urls`, `image_urls`, `storage_url`)
4. Client uploads file to presigned PUT URL
5. Backend returns public URL to client
6. Client fetches image directly from S3 using public URL (no auth required)

**Target State:**
- Database stores only S3 keys (e.g., `daily-checkins/user-id/file.webp`)
- All image access requires authenticated API call
- Backend generates short-lived presigned GET URLs on every read
- SeaweedFS has anonymous read access disabled

## Goals / Non-Goals

**Goals:**
- Secure image access through authenticated API calls only
- Store S3 keys in database instead of full URLs
- Generate presigned GET URLs with configurable expiry (1h default, 4h for playbooks)
- Migrate existing data without downtime
- Remove anonymous read access from SeaweedFS

**Non-Goals:**
- Image encryption at rest (SeaweedFS handles encryption)
- CDN caching (presigned URLs change on every request)
- Refresh token mechanism for long-running sessions (out of scope for v1)
- Presigned URLs for model_book AI analysis (can use internal S3 endpoint directly)

## Decisions

### Decision 1: Store Bucket + Key vs Key-only vs Full URL in Database

**Choice:** Store both bucket name and object key as a combined `{bucket}/{key}` string (e.g., `tradesensei/daily-checkins/user-id/file.webp`)

**Why bucket must be stored:**
- `generate_presigned_url()` requires both Bucket and Key parameters
- Reading bucket from `settings.storage_bucket` at read time is fragile: if the bucket name ever changes (migration, multi-tenant), existing DB records become unresolvable
- The bucket name is part of the object's identity, not a runtime configuration detail

**Format:** `{bucket}/{object-key}` — the bucket is the first path segment, the rest is the object key.
```python
# In storage_service.py
stored_ref = f"{settings.storage_bucket}/{object_key}"
# e.g.: "tradesensei/daily-checkins/user-id/abc123.webp"

# When generating presigned URL:
bucket, key = stored_ref.split("/", 1)
url = s3_client.generate_presigned_url(
    ClientMethod="get_object",
    Params={"Bucket": bucket, "Key": key},
    ExpiresIn=expires_in,
)
```

**Alternatives Considered:**
- Store key only (e.g., `daily-checkins/user-id/file.webp`) and read bucket from settings → Fragile: bucket rename breaks all existing records
- Store full public URL → Requires complex URL parsing to reconstruct key+bucket; static URLs leak to DB
- Store bucket and key as separate DB columns → Overkill for string columns; `{bucket}/{key}` is simpler and self-contained

**Rationale:** Storing `{bucket}/{key}` is the minimal self-contained reference needed to regenerate presigned URLs at any future point, regardless of configuration changes.

### Decision 2: Presigned URL Expiry Times

**Choice:** Use different expiry times based on use case
- Trade images / daily checkins: 1 hour (3600s)
- Playbook attachments: 4 hours (14400s)

**Alternatives Considered:**
- Single expiry time for all → Doesn't match usage patterns
- Very short expiry (5 minutes) → Would break normal browsing sessions
- Very long expiry (24 hours) → Reduces security benefit

**Rationale:** Trade images are typically viewed briefly during analysis. Playbooks are reference materials that users keep open longer. 1h is standard for presigned URLs, 4h accommodates longer sessions without being too permissive.

### Decision 3: Presigned URL Generation Location

**Choice:** Generate presigned URLs in Pydantic schemas using `model_validator`

**Alternatives Considered:**
- Generate in API route handlers → Violates layer separation
- Generate in service layer → Would require passing storage_service to every service method
- Generate in repository layer → Repositories should only handle DB queries

**Rationale:** Pydantic schemas are the serialization layer. Using `model_validator(mode='after')` allows us to transform stored keys into presigned URLs during serialization, keeping the logic in one place and maintaining clean layer separation.

### Decision 4: Migration Strategy

**Choice:** Data-only migration (no code deploy during migration)

**Migration Steps:**
1. Write and test Alembic migration that strips URL prefixes to extract keys
2. Deploy migration during low-traffic window
3. Deploy code changes (backward compatible - can read both keys and URLs)
4. Remove SeaweedFS anonymous read access after confirming code works

**Alternatives Considered:**
- Blue-green deployment with dual writes → More complex, unnecessary for this change
- Single atomic deploy (migration + code + infra) → Too risky

**Rationale:** Data migration is reversible (we can reconstruct URLs from keys if needed). Keeping code backward compatible during migration reduces risk. Infrastructure change happens last after validation.

### Decision 5: Frontend Caching Strategy

**Choice:** No long-term caching of presigned URLs

**Alternatives Considered:**
- Cache URLs until near expiry → Adds complexity, minimal benefit
- Add refresh endpoint → Out of scope for v1

**Rationale:** Frontend already makes API calls to fetch trades/checkins. The presigned URLs are embedded in the response. React Query handles short-term caching. Long-term caching would require tracking expiry times and refresh logic - not worth the complexity for v1.

## Risks / Trade-offs

**[Risk] Presigned URLs expire during active session**  
→ **Mitigation:** 1h expiry is sufficient for normal browsing. Users can refresh the page to get new URLs. Consider adding refresh endpoint in future iteration if users report issues.

**[Risk] Frontend breaks if it caches image URLs in localStorage**  
→ **Mitigation:** Audit frontend code during implementation to ensure no long-term caching. Document in frontend PR that URLs are ephemeral.

**[Risk] Database migration fails on JSONB column updates**  
→ **Mitigation:** Test migration thoroughly on staging data. Include rollback script. Run during low-traffic window. Monitor for errors.

**[Risk] Performance impact of generating presigned URLs on every request**  
→ **Mitigation:** Presigned URL generation is fast (local signing operation, no S3 API call). Benchmark before/after. If needed, add short TTL cache (5 minutes) in future iteration.

**[Risk] Breaking change to frontend API contract**  
→ **Mitigation:** This IS a breaking change (`public_url` → `key` in upload responses). Coordinate with frontend team. Deploy backend first with both old and new fields during transition period if needed.

## Migration Plan

### Phase 1: Database Migration
1. Create Alembic migration:
   ```python
   # Extract {bucket}/{key} from full URL
   # https://s3.tss.framas.cloud/tradesensei/daily-checkins/user/file.webp
   # → tradesensei/daily-checkins/user/file.webp
   
   # Strip only the host prefix (STORAGE_PUBLIC_URL), keep bucket + key
   base = f"{settings.storage_public_url}/"
   stored_ref = existing_url.removeprefix(base)
   # Result: "tradesensei/daily-checkins/user/file.webp"
   
   UPDATE daily_checkins SET screenshot_urls = strip_host_prefix(screenshot_urls, base)
   UPDATE trades SET image_urls = strip_host_prefix(image_urls, base)
   UPDATE playbook_attachments SET storage_url = strip_host_prefix(storage_url, base)
   ```
2. Test on staging database
3. Run during low-traffic window (e.g., 2 AM UTC)
4. Verify data integrity after migration

### Phase 2: Backend Deployment
1. Deploy code changes:
   - Update `StorageService` to add `generate_presigned_get_url()` method
   - Update schemas to return `key` instead of `public_url` in upload responses
   - Update schemas to generate presigned URLs in read responses
   - Update API endpoints and services
2. Run smoke tests on key endpoints:
   - `POST /checkins/upload-url`
   - `GET /checkins`
   - `POST /trades/upload-image-url`
   - `GET /trades`
   - `POST /playbook-attachments/upload-url`
   - `GET /playbook-attachments`
3. Verify presigned URLs work and images load correctly

### Phase 3: Infrastructure Change
1. Update SeaweedFS `security.json` to remove anonymous read access
2. Deploy to k3s cluster
3. Verify anonymous requests are blocked (should return 403)
4. Verify authenticated requests with presigned URLs still work

### Rollback Strategy
- **Phase 1:** Revert migration if data corruption detected (reconstruct URLs from keys)
- **Phase 2:** Revert code deploy, re-enable previous version
- **Phase 3:** Re-add anonymous read to `security.json` if critical issues found

## Open Questions

1. Should the model_book (AI analysis) also receive presigned URLs, or can it use the internal S3 endpoint directly?
   - **Recommendation:** Use internal S3 endpoint (http://seaweedfs:8333) with AWS credentials. No need for presigned URLs for internal service-to-service communication.

2. Do we need a `refresh_presigned_url` endpoint for long-running sessions?
   - **Recommendation:** Not for v1. Monitor user behavior and add if needed. Most sessions don't last >1 hour.

3. Expiry for playbook attachments — 4h enough or should it be request-scoped?
   - **Recommendation:** 4h is reasonable. Can adjust based on usage data.

4. Should presigned URLs be bound to user sessions (JWT token)?
   - **Problem:** S3/SeaweedFS validates presigned URLs independently - it only checks AWSAccessKeyId, Expires, and Signature. S3 has no concept of our JWT sessions.
   - **Session binding would require:** Building a proxy in front of S3 that validates JWT for every image request, then forwards to S3. This kills performance and browser caching.
   - **Current approach is better:** 
     - Only authenticated users can call the API endpoints that generate presigned URLs
     - URLs expire after 1h (short-lived)
     - Leaked URLs are only temporarily valid
     - Much better performance (direct S3 access, browser can cache)
   - **Recommendation:** Keep current design. If session binding becomes critical, consider image streaming through backend proxy (accept performance trade-off).
