"use client";

import { useState, useRef } from "react";
import { generateScreenshotUploadUrlApiV1CheckinsScreenshotUploadUrlPost } from "@/lib/api/index";
import { ImagePlus, Loader2, AlertCircle } from "lucide-react";

interface Props {
  onUploaded: (url: string) => void;
}

export function ScreenshotUploader({ onUploaded }: Props) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const res = await generateScreenshotUploadUrlApiV1CheckinsScreenshotUploadUrlPost({
        body: {
          filename: file.name,
          content_type: file.type,
        },
      });

      if (res.error) {
        setError(
          res.response?.status === 503
            ? "Screenshot upload unavailable"
            : "Failed to get upload URL"
        );
        setIsUploading(false);
        return;
      }

      if (!res.data) {
        setError("Failed to get upload URL");
        setIsUploading(false);
        return;
      }

      const { presigned_url, public_url } = res.data.data;

      const uploadRes = await fetch(presigned_url, {
        method: "PUT",
        body: file,
        headers: {
          "Content-Type": file.type,
        },
      });

      if (!uploadRes.ok) {
        setError("Failed to upload file");
        setIsUploading(false);
        return;
      }

      onUploaded(public_url);
    } catch (err) {
      console.error(err);
      setError("An unexpected error occurred");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div>
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png, image/jpeg, image/webp"
          className="hidden"
          onChange={handleFileChange}
          disabled={isUploading || error === "Screenshot upload unavailable"}
        />
        <button
          type="button"
          disabled={isUploading || error === "Screenshot upload unavailable"}
          onClick={() => fileInputRef.current?.click()}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-border bg-background text-foreground hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isUploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ImagePlus className="w-4 h-4" />
          )}
          {isUploading ? "Uploading..." : "Add Screenshot"}
        </button>
      </div>
      {error && (
        <div className="mt-2 flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
    </div>
  );
}
