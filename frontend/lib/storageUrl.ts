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

type StorageAccessMode = "proxy" | "direct";

function getStorageAccessMode(): StorageAccessMode {
  const mode = process.env.NEXT_PUBLIC_STORAGE_ACCESS_MODE;
  return mode === "direct" ? "direct" : "proxy";
}

/**
 * Resolves a storage URL for use in <img> tags.
 *
 * - `proxy` mode (default): always tunnel through /api/storage-proxy
 * - `direct` mode: return URL unchanged
 * - Relative paths are returned unchanged
 */
export function resolveStorageUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith("/")) return url;
  if (url.startsWith("blob:") || url.startsWith("data:")) return url;

  if (getStorageAccessMode() === "direct") return url;
  return `/api/storage-proxy?url=${encodeURIComponent(url)}`;
}

/**
 * Returns the URL to use for a presigned PUT upload.
 *
 * Same mode as resolveStorageUrl: `proxy` tunnels, `direct` bypasses.
 */
export function storageUploadUrl(presignedUrl: string): string {
  return resolveStorageUrl(presignedUrl);
}
