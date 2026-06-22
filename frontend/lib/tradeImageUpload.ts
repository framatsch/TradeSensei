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

import { storageUploadUrl } from "@/lib/storageUrl";

export interface TradeImageUploadUrls {
  presigned_url: string;
  key: string;
}

export type TradeImageUploadUrlRequester = (
  filename: string,
  contentType: string
) => Promise<TradeImageUploadUrls>;

export async function uploadTradeImages(
  files: File[],
  requestUploadUrl: TradeImageUploadUrlRequester,
  putFile: typeof fetch = fetch
): Promise<string[]> {
  const uploadedUrls: string[] = [];

  for (const file of files) {
    const contentType = file.type || "application/octet-stream";
    const { presigned_url, key } = await requestUploadUrl(file.name, contentType);

    const response = await putFile(storageUploadUrl(presigned_url), {
      method: "PUT",
      headers: {
        "Content-Type": contentType,
      },
      body: file,
    });

    if (!response.ok) {
      throw new Error(`Upload failed for ${file.name} (${response.status})`);
    }

    uploadedUrls.push(key);
  }

  return uploadedUrls;
}
