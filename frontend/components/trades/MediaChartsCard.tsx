/**
 * MediaChartsCard — tabs for TradingView embed, screenshot gallery, and data chart.
 * Supports drag-and-drop upload, lightbox, and inline TradingView link editing.
 */

"use client";

import { useRef, useState, useCallback } from "react";
import Image from "next/image";
import { useUploadScreenshot, useDeleteScreenshot } from "@/hooks/useScreenshots";
import { useUpdateTrade } from "@/hooks/useTrade";
import type { Trade } from "@/lib/types";

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function resolveUrl(url: string): string {
  if (url.startsWith("http")) return url;
  return `${BACKEND_BASE}${url}`;
}

// ── Lightbox ─────────────────────────────────────────────────────────────────

function Lightbox({
  src,
  onClose,
}: {
  src: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-w-5xl max-h-[90vh] w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white/70 hover:text-white text-sm flex items-center gap-1"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
          Close
        </button>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={resolveUrl(src)}
          alt="Screenshot"
          className="rounded-lg w-full h-full object-contain max-h-[90vh]"
        />
      </div>
    </div>
  );
}

// ── TradingView tab ───────────────────────────────────────────────────────────

function TradingViewTab({ trade }: { trade: Trade }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(trade.tradingview_link ?? "");
  const { mutate: updateTrade, isPending } = useUpdateTrade(trade.id);

  const save = () => {
    updateTrade(
      { tradingview_link: draft || null },
      { onSuccess: () => setEditing(false) }
    );
  };

  if (editing || !trade.tradingview_link) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
        {!trade.tradingview_link && !editing && (
          <p className="text-sm text-slate-400">No TradingView link set.</p>
        )}
        {editing ? (
          <div className="w-full max-w-lg space-y-3">
            <label className="block text-xs text-slate-500 mb-1">TradingView Chart URL</label>
            <input
              type="url"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="https://www.tradingview.com/chart/..."
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-sm text-slate-800 dark:text-slate-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2">
              <button
                onClick={save}
                disabled={isPending}
                className="px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md transition-colors"
              >
                {isPending ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => { setEditing(false); setDraft(trade.tradingview_link ?? ""); }}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-md transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 border border-blue-300 dark:border-blue-700 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            Add TradingView Link
          </button>
        )}
      </div>
    );
  }

  // Convert a TradingView chart URL to an embed URL if possible
  const embedSrc = trade.tradingview_link.replace(
    /tradingview\.com\/chart\//,
    "tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol="
  );
  const isEmbeddable = trade.tradingview_link.includes("tradingview.com");

  return (
    <div className="relative w-full h-full">
      {isEmbeddable ? (
        <iframe
          src={embedSrc}
          className="w-full h-full rounded-b-xl border-0"
          allowFullScreen
          title="TradingView Chart"
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-full gap-3">
          <p className="text-sm text-slate-500">External link (not embeddable directly):</p>
          <a
            href={trade.tradingview_link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:underline text-sm break-all px-4 text-center"
          >
            {trade.tradingview_link}
          </a>
        </div>
      )}
      <button
        onClick={() => setEditing(true)}
        className="absolute top-2 right-2 p-1.5 rounded-md bg-slate-900/60 text-white/70 hover:text-white hover:bg-slate-900/80 transition-colors"
        title="Edit link"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
    </div>
  );
}

// ── Screenshots tab ───────────────────────────────────────────────────────────

function ScreenshotsTab({ trade }: { trade: Trade }) {
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { mutate: upload, isPending: uploading } = useUploadScreenshot(trade.id);
  const { mutate: deleteShot, isPending: deleting } = useDeleteScreenshot(trade.id);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      Array.from(files).forEach((file) => upload(file));
    },
    [upload]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const screenshots = trade.screenshots ?? [];

  return (
    <>
      {lightboxSrc && (
        <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
      )}

      <div className="flex flex-col h-full gap-3 p-4">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 ${
            isDragging
              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
              : "border-slate-300 dark:border-slate-600 hover:border-blue-400 hover:bg-slate-50 dark:hover:bg-slate-700/40"
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
            <span className="text-sm text-blue-500 animate-pulse">Uploading…</span>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-7 h-7 text-slate-400">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span className="text-xs text-slate-500">
                Drag & drop or <span className="text-blue-500 font-medium">click to upload</span>
              </span>
              <span className="text-xs text-slate-400">PNG, JPG, GIF, WebP · max 20 MB</span>
            </>
          )}
        </div>

        {/* Gallery */}
        {screenshots.length > 0 ? (
          <div className="grid grid-cols-3 gap-2 overflow-y-auto flex-1">
            {screenshots.map((url) => (
              <div key={url} className="group relative aspect-video bg-slate-100 dark:bg-slate-700 rounded-lg overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={resolveUrl(url)}
                  alt="screenshot"
                  className="w-full h-full object-cover cursor-pointer transition-transform group-hover:scale-105"
                  onClick={() => setLightboxSrc(url)}
                />
                <button
                  onClick={() => deleteShot(url)}
                  disabled={deleting}
                  className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 p-1 rounded-md bg-black/60 text-white hover:bg-red-600/80 transition-all"
                  title="Delete screenshot"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-center text-sm text-slate-400 py-2">No screenshots yet.</p>
        )}
      </div>
    </>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

type Tab = "tradingview" | "screenshots";

export function MediaChartsCard({ trade }: { trade: Trade }) {
  const [activeTab, setActiveTab] = useState<Tab>("tradingview");

  const screenshotCount = trade.screenshots?.length ?? 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col" style={{ minHeight: "22rem" }}>
      {/* Tab bar */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 shrink-0">
        {(["tradingview", "screenshots"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`relative px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "border-b-2 border-blue-500 text-blue-600 dark:text-blue-400"
                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            }`}
          >
            {tab === "tradingview" && "TradingView"}
            {tab === "screenshots" && (
              <>
                Screenshots
                {screenshotCount > 0 && (
                  <span className="ml-1.5 text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded-full">
                    {screenshotCount}
                  </span>
                )}
              </>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden rounded-b-xl">
        {activeTab === "tradingview" && <TradingViewTab trade={trade} />}
        {activeTab === "screenshots" && <ScreenshotsTab trade={trade} />}
      </div>
    </div>
  );
}
