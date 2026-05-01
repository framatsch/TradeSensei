export interface TradeImageUploadUrls {
  presigned_url: string;
  public_url: string;
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
    const { presigned_url, public_url } = await requestUploadUrl(file.name, contentType);

    const response = await putFile(presigned_url, {
      method: "PUT",
      headers: {
        "Content-Type": contentType,
      },
      body: file,
    });

    if (!response.ok) {
      throw new Error(`Upload failed for ${file.name} (${response.status})`);
    }

    uploadedUrls.push(public_url);
  }

  return uploadedUrls;
}
