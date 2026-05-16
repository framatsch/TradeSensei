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

"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useTradeImageUploadUrl } from "@/hooks/useTrade";

interface Props {
  onUploaded: (urls: string[]) => void;
  disabled?: boolean;
}

export function TradeScreenshotUploader({ onUploaded, disabled = false }: Props) {
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [pasteHint, setPasteHint] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadUrlMutation = useTradeImageUploadUrl();

  const handleFiles = useCallback(async (files: FileList | File[] | null) => {
    if (!files || files.length === 0) return;
    const validFiles = Array.from(files).filter(f => f.type.startsWith("image/"));
    if (validFiles.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      const uploadedUrls: string[] = [];

      for (const file of validFiles) {
        // Handle max size (20MB)
        if (file.size > 20 * 1024 * 1024) {
          setError(`File ${file.name} is too large (max 20MB)`);
          continue;
        }

        const res = await uploadUrlMutation.mutateAsync({
          filename: file.name,
          contentType: file.type,
        });

        const uploadRes = await fetch(res.presigned_url, {
          method: "PUT",
          body: file,
          headers: {
            "Content-Type": file.type,
          },
        });

        if (!uploadRes.ok) {
          setError("Failed to upload file");
          continue;
        }

        uploadedUrls.push(res.public_url);
      }

      if (uploadedUrls.length > 0) {
        onUploaded(uploadedUrls);
      }
    } catch (err) {
      console.error(err);
      setError("An unexpected error occurred");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }, [onUploaded, uploadUrlMutation]);

  // Clipboard paste
  useEffect(() => {
    const handler = (e: ClipboardEvent) => {
      if (disabled) return;
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
  }, [handleFiles, disabled]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return;
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 ${
          disabled
            ? "opacity-50 cursor-not-allowed pointer-events-none"
            : isDragging
            ? "border-primary bg-[color-mix(in_srgb,var(--primary)_5%,transparent)]"
            : pasteHint
            ? "border-primary bg-[color-mix(in_srgb,var(--primary)_5%,transparent)]"
            : "border-border hover:border-primary hover:bg-muted/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={isUploading || disabled}
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
