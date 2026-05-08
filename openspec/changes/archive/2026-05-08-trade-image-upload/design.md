## Context

Traders often need to attach context to their trades, such as screenshots of charts or setup patterns. A similar capability already exists for daily check-ins (`daily-checkin-system`). This change extends the functionality to individual trades by allowing users to upload images to S3 and link the resulting URLs to the trade.

## Goals / Non-Goals

**Goals:**
- Allow users to request an S3 presigned URL specifically for a trade.
- Store an array of image URLs (`image_urls`) on the Trade model.
- Support creating, updating, and viewing these images on the frontend trade detail page.

**Non-Goals:**
- Server-side image processing or resizing.
- Storing images as binary blobs in the PostgreSQL database.
- Generating thumbnails (UI can rely on CSS object-fit for now).

## Decisions

**Decision 1: Reusing S3 Upload Flow**
We will reuse the two-step upload flow used by the daily check-ins:
1. Client requests a presigned PUT URL.
2. Client uploads to S3 directly.
3. Client includes the final URL in the trade's `image_urls` payload when updating/creating the trade.

**Rationale:** Keeps the FastAPI backend stateless, avoids binary stream parsing in Python, and reuses the `STORAGE_PUBLIC_URL` logic already configured for check-ins.

**Decision 2: Image Array on Trade Model**
Trade model gets a JSONB field `image_urls` (list of strings).
**Rationale:** Simpler than a dedicated `TradeImage` relationship table since metadata beyond the URL isn't strictly required right now. It matches the `screenshot_urls` array on `DailyCheckin`.

## Risks / Trade-offs

- [Risk] Unvalidated URLs in `image_urls` could lead to SSRF or rendering malicious external images.
  → Mitigation: Backend will validate that incoming URLs match the configured `STORAGE_PUBLIC_URL` prefix before accepting them, just as it does for check-ins. If `STORAGE_PUBLIC_URL` is empty, updates containing images are rejected.
