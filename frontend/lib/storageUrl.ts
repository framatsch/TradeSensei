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
 * Returns true if the hostname is not directly reachable by a browser client
 * (localhost, Kubernetes cluster-internal DNS, RFC-1918 private IPs).
 *
 * External hostnames (e.g. *.amazonaws.com, custom CDN domains) return false
 * and will be used directly by the browser without going through the proxy —
 * preserving performance for production S3/CloudFront setups.
 */
function needsProxy(hostname: string): boolean {
  // Localhost variants
  if (
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "::1" ||
    hostname === "0.0.0.0"
  ) return true;

  // Kubernetes cluster-internal DNS (*.svc.cluster.local, *.cluster.local)
  if (hostname.endsWith(".cluster.local")) return true;

  // RFC-1918 private IP ranges (10.x, 172.16-31.x, 192.168.x)
  if (/^10\./.test(hostname)) return true;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(hostname)) return true;
  if (/^192\.168\./.test(hostname)) return true;

  return false;
}

/**
 * Resolves a storage URL for use in <img> tags.
 *
 * - Internal URLs (localhost, Kubernetes cluster DNS, private IPs) are
 *   tunnelled through /api/storage-proxy so the browser never needs direct
 *   access to the storage backend.
 * - External URLs (real S3, CloudFront, etc.) are returned as-is so the
 *   browser fetches them directly — no proxy overhead, full CDN performance.
 * - Relative paths are returned unchanged.
 */
export function resolveStorageUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith("/")) return url;

  try {
    const { hostname } = new URL(url);
    if (needsProxy(hostname)) {
      return `/api/storage-proxy?url=${encodeURIComponent(url)}`;
    }
  } catch {
    // not a valid URL — return as-is
  }

  return url;
}

/**
 * Returns the URL to use for a presigned PUT upload.
 *
 * Same logic as resolveStorageUrl: internal storage goes through the proxy,
 * external S3 endpoints are used directly (browsers can PUT to public S3).
 */
export function storageUploadUrl(presignedUrl: string): string {
  return resolveStorageUrl(presignedUrl);
}
