/**
 * MediaChartsCard — TradingView chart widget + screenshot gallery.
 * Chart always shows based on trade.symbol.
 * TradingView link is stored as meta-info and shown as an external link.
 * Screenshots support drag-and-drop, file picker, and clipboard paste.
 */

"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { useUploadScreenshot, useDeleteScreenshot } from "@/hooks/useScreenshots";
import { useUpdateTrade } from "@/hooks/useTrade";
import type { Trade } from "@/lib/types";

const BACKEND_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function resolveUrl(url: string): string {
  if (url.startsWith("http")) return url;
  return `${BACKEND_BASE}${url}`;
}

// ── Lightbox ──────────────────────────────────────────────────────────────────

function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

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
          className="absolute -top-9 right-0 text-white/70 hover:text-white text-sm flex items-center gap-1"
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
          className="rounded-lg w-full object-contain max-h-[90vh]"
        />
      </div>
    </div>
  );
}

// ── TradingView Widget ────────────────────────────────────────────────────────

function TradingViewWidget({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "tradingview-widget-container__widget";
    wrapper.style.height = "100%";
    wrapper.style.width = "100%";
    container.appendChild(wrapper);

    const script = document.createElement("script");
    script.src =
      "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol,
      interval: "D",
      timezone: "Etc/UTC",
      theme: "dark",
      style: "1",
      locale: "en",
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      calendar: false,
      support_host: "https://www.tradingview.com",
    });
    container.appendChild(script);
  }, [symbol]);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-container w-full h-full"
      style={{ minHeight: "320px" }}
    />
  );
}

// ── TradingView tab ───────────────────────────────────────────────────────────

function TradingViewTab({ trade }: { trade: Trade }) {
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
      {/* Chart — always shown based on trade symbol */}
      <div className="flex-1 min-h-0">
        <TradingViewWidget symbol={trade.symbol} />
      </div>

      {/* TradingView link meta row */}
      <div className="shrink-0 border-t border-slate-200 dark:border-slate-700 px-4 py-2 flex items-center gap-2 bg-slate-50 dark:bg-slate-900/40 rounded-b-xl">
        {editingLink ? (
          <>
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") saveLink(); if (e.key === "Escape") setEditingLink(false); }}
              placeholder="https://www.tradingview.com/chart/..."
              className="flex-1 rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-xs text-slate-800 dark:text-slate-100 px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <button
              onClick={saveLink}
              disabled={isPending}
              className="px-2.5 py-1 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md transition-colors"
            >
              {isPending ? "…" : "Save"}
            </button>
            <button
              onClick={() => { setEditingLink(false); setDraft(trade.tradingview_link ?? ""); }}
              className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 rounded-md transition-colors"
            >
              Cancel
            </button>
          </>
        ) : trade.tradingview_link ? (
          <>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3.5 h-3.5 text-slate-400 shrink-0">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            <a
              href={trade.tradingview_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-xs text-blue-500 hover:underline truncate"
              title={trade.tradingview_link}
            >
              {trade.tradingview_link}
            </a>
            <a
              href={trade.tradingview_link}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 px-2 py-1 text-xs text-slate-600 dark:text-slate-300 hover:text-blue-500 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
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
              className="shrink-0 p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
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
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-blue-500 transition-colors"
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

  const screenshots = trade.screenshots ?? [];

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
              ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
              : pasteHint
              ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20"
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
          ) : pasteHint ? (
            <span className="text-sm text-emerald-500 font-medium">Pasted!</span>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-6 h-6 text-slate-400">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span className="text-xs text-slate-500">
                <span className="text-blue-500 font-medium">Click</span> or drag & drop
                <span className="mx-1 text-slate-300 dark:text-slate-600">·</span>
                <kbd className="px-1 py-0.5 text-xs font-mono bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded">⌘V</kbd> to paste
              </span>
              <span className="text-xs text-slate-400">PNG, JPG, GIF, WebP · max 20 MB</span>
            </>
          )}
        </div>

        {/* Gallery */}
        {screenshots.length > 0 ? (
          <div className="grid grid-cols-3 gap-2 overflow-y-auto flex-1">
            {screenshots.map((url) => (
              <div
                key={url}
                className="group relative aspect-video bg-slate-100 dark:bg-slate-700 rounded-lg overflow-hidden"
              >
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
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
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
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-col"
      style={{ minHeight: "22rem" }}
    >
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
            {tab === "tradingview" && "Chart"}
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
