"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { generateScreenshotUploadUrlApiV1CheckinsScreenshotUploadUrlPost } from "@/lib/api/index";

interface Props {
  onUploaded: (url: string) => void;
}

export function ScreenshotUploader({ onUploaded }: Props) {
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [pasteHint, setPasteHint] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList | File[] | null) => {
    if (!files || files.length === 0) return;
    const file = files[0]; // Upload one by one for now (or handle loop)

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
  }, [onUploaded]);

  // Clipboard paste
  useEffect(() => {
    const handler = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles: File[] = [];
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) imageFiles.push(file);
        }
      }
      if (imageFiles.length > 0) {
        e.preventDefault();
        handleFiles(imageFiles);
        // Brief visual feedback
        setPasteHint(true);
        setTimeout(() => setPasteHint(false), 1500);
      }
    };
    window.addEventListener("paste", handler);
    return () => window.removeEventListener("paste", handler);
  }, [handleFiles]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 ${
          isDragging
            ? "border-primary bg-[color-mix(in_srgb,hsl(var(--primary))_5%,transparent)]"
            : pasteHint
            ? "border-primary bg-[color-mix(in_srgb,hsl(var(--primary))_5%,transparent)]"
            : "border-border hover:border-primary hover:bg-muted/50"
        } ${error === "Screenshot upload unavailable" ? "opacity-50 cursor-not-allowed pointer-events-none" : ""}`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isUploading || error === "Screenshot upload unavailable"}
        />
        {isUploading ? (
          <span className="text-sm text-primary animate-pulse">Uploading…</span>
        ) : pasteHint ? (
          <span className="text-sm text-primary font-medium">Pasted!</span>
        ) : (
          <>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6 text-muted-foreground">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="text-xs text-muted-foreground">
              <span className="text-primary font-medium">Click</span> or drag & drop
              <span className="mx-1 text-muted-foreground/40">·</span>
              <kbd className="px-1 py-0.5 text-xs font-mono bg-secondary border border-border dark:border-border rounded">⌘V</kbd> to paste
            </span>
            <span className="text-xs text-muted-foreground">PNG, JPG, GIF, WebP · max 20 MB</span>
            <span className="text-xs text-muted-foreground">Only static screenshots are supported. Live chart embeds are not used.</span>
          </>
        )}
      </div>
      {error && (
        <div className="mt-2 text-center text-sm text-destructive font-medium">
          {error}
        </div>
      )}
    </div>
  );
}
