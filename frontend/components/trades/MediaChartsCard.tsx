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
 * MediaChartsCard — Smart trade chart (Market Data Hub / TradingView fallback)
 * + screenshot gallery.
 *
 * Screenshots support drag-and-drop, file picker, and clipboard paste.
 *
 * All browser-side API calls go through the Next.js reverse proxy at
 * `/api/proxy/v1/...` — absolute URLs are not needed here.
 */

"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Maximize2, Minimize2 } from "lucide-react";
import { useUploadScreenshot, useDeleteScreenshot } from "@/hooks/useScreenshots";
import { useUpdateTrade } from "@/hooks/useTrade";
import type { Trade, LogicalExecution } from "@/lib/types";
import { TradeChart } from "@/components/charts/TradeChart";
import { resolveStorageUrl } from "@/lib/storageUrl";

function resolveUrl(url: string): string {
  if (url.startsWith("http")) return resolveStorageUrl(url);
  return `/api/proxy${url}`;
}

// ── Chart tab (Market Data Hub → TradingView fallback) ────────────────────────

function ChartTab({ trade, executions }: { trade: Trade; executions?: LogicalExecution[] }) {
  return (
    <div className="w-full h-full">
      <TradeChart trade={trade} executions={executions} />
    </div>
  );
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/90 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Screenshot viewer"
      onClick={onClose}
    >
      {/* Top bar */}
      <div className="shrink-0 flex justify-end px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="text-white/60 hover:text-white text-sm flex items-center gap-1.5 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          Close (Esc)
        </button>
      </div>
      {/* Image — fills remaining space */}
      <div
        className="flex-1 flex items-center justify-center overflow-hidden px-4 pb-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={resolveUrl(src)}
          alt="Screenshot"
          className="rounded-lg object-contain w-full h-full"
          style={{ maxHeight: "100%", maxWidth: "100%" }}
        />
      </div>
    </div>
  );
}

// ── TradingView tab ───────────────────────────────────────────────────────────

function TradingViewTab({ trade, executions }: { trade: Trade; executions?: LogicalExecution[] }) {
  const [editingLink, setEditingLink] = useState(false);
  const [draft, setDraft] = useState(trade.tradingview_link ?? "");
  const { mutate: updateTrade, isPending } = useUpdateTrade(trade.id);

  const saveLink = () => {
    updateTrade(
      { tradingview_link: draft.trim() || null },
      { onSuccess: () => setEditingLink(false) }
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chart — grows to fill available height */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ChartTab trade={trade} executions={executions} />
      </div>

      {/* TradingView link meta row */}
      <div className="shrink-0 border-t border-border px-4 py-2 flex items-center gap-2 bg-zinc-100/40 dark:bg-zinc-900/40 rounded-b-xl">
        {editingLink ? (
          <>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") saveLink(); if (e.key === "Escape") setEditingLink(false); }}
              placeholder="https://www.tradingview.com/chart/..."
              className="flex-1 rounded-md border border-border dark:border-border bg-card text-xs text-zinc-800 dark:text-foreground px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
              autoFocus
            />
            <button
              onClick={saveLink}
              disabled={isPending}
              className="px-2.5 py-1 text-xs font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-white rounded-md transition-colors"
            >
              {isPending ? "…" : "Save"}
            </button>
            <button
              onClick={() => { setEditingLink(false); setDraft(trade.tradingview_link ?? ""); }}
              className="px-2.5 py-1 text-xs text-muted-foreground hover:text-zinc-700 dark:hover:text-zinc-300 rounded-md transition-colors"
            >
              Cancel
            </button>
          </>
        ) : trade.tradingview_link ? (
          <>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5 text-zinc-400 shrink-0">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <a
              href={trade.tradingview_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-xs text-primary hover:underline truncate"
              title={trade.tradingview_link}
            >
              {trade.tradingview_link}
            </a>
            <a
              href={trade.tradingview_link}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 px-2 py-1 text-xs text-zinc-600 dark:text-zinc-300 hover:text-primary dark:hover:text-primary transition-colors flex items-center gap-1"
              title="Open in TradingView"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              Open
            </a>
            <button
              onClick={() => setEditingLink(true)}
              className="shrink-0 p-1 rounded text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
              title="Edit link"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
          </>
        ) : (
          <button
            onClick={() => setEditingLink(true)}
            className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-primary transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
              <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Add TradingView chart link
          </button>
        )}
      </div>
    </div>
  );
}

// ── Screenshots tab ───────────────────────────────────────────────────────────

function ScreenshotsTab({ trade }: { trade: Trade }) {
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [pasteHint, setPasteHint] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const { mutate: upload, isPending: uploading } = useUploadScreenshot(trade.id);
  const { mutate: deleteShot, isPending: deleting } = useDeleteScreenshot(trade.id);

  const handleFiles = useCallback(
    (files: FileList | File[] | null) => {
      if (!files) return;
      Array.from(files).forEach((file) => {
        if (file.type.startsWith("image/")) upload(file);
      });
    },
    [upload]
  );

  // Clipboard paste — global on this tab
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

  const screenshots = trade.image_urls ?? [];

  // Close lightbox if the currently viewed image is deleted
  if (lightboxSrc && !screenshots.includes(lightboxSrc)) {
    setLightboxSrc(null);
  }

  return (
    <>
      {lightboxSrc && (
        <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div className="flex flex-col h-full gap-3 p-4">
        {/* Drop / paste zone */}
        <div
          ref={dropZoneRef}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 ${
            isDragging
              ? "border-primary bg-blue-50 dark:bg-blue-900/20"
              : pasteHint
              ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
              : "border-border dark:border-border hover:border-blue-400 hover:bg-zinc-50 dark:hover:bg-zinc-700/40"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {uploading ? (
            <span className="text-sm text-primary animate-pulse">Uploading…</span>
          ) : pasteHint ? (
            <span className="text-sm text-emerald-500 font-medium">Pasted!</span>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6 text-zinc-400">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span className="text-xs text-muted-foreground">
                <span className="text-primary font-medium">Click</span> or drag & drop
                <span className="mx-1 text-zinc-300 dark:text-zinc-600">·</span>
                <kbd className="px-1 py-0.5 text-xs font-mono bg-secondary border border-border dark:border-border rounded">⌘V</kbd> to paste
              </span>
              <span className="text-xs text-zinc-400">PNG, JPG, GIF, WebP · max 20 MB</span>
            </>
          )}
        </div>

        {/* Gallery */}
        {screenshots.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 overflow-y-auto flex-1">
            {screenshots.map((url) => (
              <div
                key={url}
                className="group relative aspect-[4/3] bg-secondary rounded-xl overflow-hidden"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={resolveUrl(url)}
                  alt="screenshot"
                  className="w-full h-full object-cover cursor-pointer transition-transform duration-200 group-hover:scale-105"
                  onClick={() => setLightboxSrc(url)}
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Are you sure you want to delete this screenshot?")) {
                      deleteShot(url);
                    }
                  }}
                  disabled={deleting}
                  className="absolute top-2 right-2 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 p-1.5 rounded-md bg-black/60 text-white hover:bg-red-600/80 transition-all"
                  title="Delete screenshot"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
                {/* Expand hint */}
                <div className="absolute inset-0 flex items-center justify-center opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-black/40 rounded-full p-2">
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" className="w-5 h-5">
                      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-sm text-zinc-400 py-4">No screenshots yet.</p>
        )}
      </div>
    </>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

type Tab = "tradingview" | "screenshots";

export function MediaChartsCard({ trade, executions, className }: { trade: Trade; executions?: LogicalExecution[]; className?: string }) {
  const [activeTab, setActiveTab] = useState<Tab>("tradingview");
  const [isMaximized, setIsMaximized] = useState(false);
  const screenshotCount = trade.image_urls?.length ?? 0;

  useEffect(() => {
    if (!isMaximized) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMaximized(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMaximized]);

  return (
    <div
      role={isMaximized ? "dialog" : undefined}
      aria-modal={isMaximized ? "true" : undefined}
      aria-label={isMaximized ? "Maximized trade chart" : undefined}
      className={
        isMaximized
          ? "fixed inset-0 z-50 flex flex-col bg-card w-screen h-[100dvh] pb-[env(safe-area-inset-bottom)]"
          : `solid-card flex flex-col ${className ?? "h-[520px]"}`
      }
    >
      {/* Tab bar */}
      <div className="flex items-center border-b border-border shrink-0">
        {(["tradingview", "screenshots"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab);
              if (tab !== "tradingview") setIsMaximized(false);
            }}
            className={`relative px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "border-b-2 border-primary text-primary dark:text-primary"
                : "text-muted-foreground hover:text-zinc-700 dark:hover:text-zinc-300"
            }`}
          >
            {tab === "tradingview" && "Chart"}
            {tab === "screenshots" && (
              <>
                Screenshots
                {screenshotCount > 0 && (
                  <span className="ml-1.5 text-xs bg-blue-100 dark:bg-blue-900/50 text-primary dark:text-primary px-1.5 py-0.5 rounded-full">
                    {screenshotCount}
                  </span>
                )}
              </>
            )}
          </button>
        ))}
        {activeTab === "tradingview" && (
          <button
            type="button"
            onClick={() => setIsMaximized((prev) => !prev)}
            aria-label={isMaximized ? "Restore chart" : "Maximize chart"}
            title={isMaximized ? "Restore chart" : "Maximize chart"}
            className="lg:hidden ml-auto mr-2 inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            {isMaximized ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        )}
      </div>

      {/* Tab content */}
      <div className={`flex-1 overflow-hidden ${isMaximized ? "" : "rounded-b-xl"}`}>
        {activeTab === "tradingview" && <TradingViewTab trade={trade} executions={executions} />}
        {activeTab === "screenshots" && <ScreenshotsTab trade={trade} />}
      </div>
    </div>
  );
}
