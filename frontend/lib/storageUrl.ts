/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * Returns the proxy URL to use for a presigned PUT upload.
 * Instead of the browser uploading directly to SeaweedFS, it goes through
 * the Next.js server so port 8333 never needs to be exposed.
 *
 * Usage:
 *   await fetch(storageUploadUrl(presignedUrl), { method: "PUT", body: file, ... })
 */
export function storageUploadUrl(presignedUrl: string): string {
  return `/api/storage-proxy?url=${encodeURIComponent(presignedUrl)}`;
}

/**
 * Resolves a storage URL (presigned S3/SeaweedFS GET URL) for use in <img> tags.
 *
 * All absolute storage URLs are tunnelled through the Next.js server-side proxy
 * at /api/storage-proxy. This means:
 *   - The storage backend (SeaweedFS/S3) never needs to be publicly exposed.
 *   - No CORS configuration is required on the storage bucket.
 *   - Mobile devices and any client that cannot reach the storage host directly
 *     still get images served correctly.
 *
 * Relative paths (e.g. /api/proxy/...) are returned unchanged.
 */
export function resolveStorageUrl(url: string): string {
  if (!url) return url;

  // Already a relative path — no transformation needed.
  if (url.startsWith("/")) return url;

  // Any absolute URL (http/https) goes through the server-side storage proxy.
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return `/api/storage-proxy?url=${encodeURIComponent(url)}`;
  }

  return url;
}
