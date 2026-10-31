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
 * CheckinForm — Unified full-width document-first detail & editor view for a Daily Check-in.
 * Desktop (lg+): Header Card on top, Left Main Pane (flex-1) for Market Notes (Markdown),
 * Right Side Pane (w-[360px] xl:w-[420px]) for Tags & Annotations, 16:9 Screenshots, and News Links.
 * Mobile (< lg): Segmented switcher between "Document" and "Details & Media".
 */

"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  X,
  Link2,
  Loader2,
  Plus,
  Trash2,
  Edit3,
  Eye,
  Columns,
  ExternalLink,
  FileText,
  Paperclip,
} from "lucide-react";
import {
  type DailyCheckinRead,
  type DailyCheckinCreate,
  type DailyCheckinUpdate,
} from "@/lib/api/types.gen";
import { ScreenshotUploader } from "@/components/checkin/ScreenshotUploader";
import { AnnotationEditor } from "@/components/checkin/AnnotationEditor";
import { useMarketIndexes } from "@/hooks/useCheckinDefinitions";
import { CheckinLightbox } from "@/components/checkin/CheckinLightbox";
import { resolveStorageUrl } from "@/lib/storageUrl";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import {
  useAssignCheckinTaxonomy,
  useRemoveCheckinTaxonomy,
} from "@/hooks/useCheckinMetadata";

export interface CheckinSaveOptions {
  bufferedTagIds: string[];
  bufferedAnnotations: Record<string, unknown>;
  closeAfterSave: boolean;
}

export function CheckinForm({
  date,
  entry,
  prevEntryDate = null,
  nextEntryDate = null,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  date: string;
  entry: DailyCheckinRead | null | undefined;
  prevEntryDate?: string | null;
  nextEntryDate?: string | null;
  onSave: (
    data: DailyCheckinCreate | DailyCheckinUpdate,
    options?: CheckinSaveOptions
  ) => Promise<void> | void;
  onDelete: () => void;
  isSaving: boolean;
  isDeleting: boolean;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isNew = !entry;

  // ── Mode & Mobile Pane state ───────────────────────────────────────────────
  const [isEditMode, setIsEditMode] = useState(
    isNew || searchParams.get("edit") === "true"
  );
  const [mobilePane, setMobilePane] = useState<"document" | "details">("document");

  // ── Form fields ────────────────────────────────────────────────────────────
  const [targetIndexIds, setTargetIndexIds] = useState<string[]>(
    entry?.target_indices?.map((index) => index.id) ?? []
  );
  const [notes, setNotes] = useState(entry?.notes ?? "");
  const [newsLink, setNewsLink] = useState("");
  const [newsLinks, setNewsLinks] = useState<string[]>(entry?.news_links ?? []);
  const [screenshotKeys, setScreenshotKeys] = useState<string[]>(
    entry?.screenshot_keys ?? []
  );
  const [screenshotPreviews, setScreenshotPreviews] = useState<string[]>(
    entry?.screenshot_urls ?? []
  );

  // Buffered annotations + tags for new (not-yet-created) check-ins
  const [bufferedAnnotations, setBufferedAnnotations] = useState<Record<string, unknown>>({});
  const [bufferedTagIds, setBufferedTagIds] = useState<string[]>([]);

  // Initialize asynchronously loaded entries without resetting drafts on same-ID refetches.
  const [initializedEntryId, setInitializedEntryId] = useState(entry?.id ?? null);
  if (entry && entry.id !== initializedEntryId) {
    setInitializedEntryId(entry.id);
    setTargetIndexIds(entry.target_indices?.map((idx) => idx.id) ?? []);
    setNotes(entry.notes ?? "");
    setNewsLinks(entry.news_links ?? []);
    setScreenshotKeys(entry.screenshot_keys ?? []);
    setScreenshotPreviews(entry.screenshot_urls ?? []);
    if (searchParams.get("edit") !== "true") {
      setIsEditMode(false);
    }
  }

  // ── Editor state ───────────────────────────────────────────────────────────
  const [notesTab, setNotesTab] = useState<"write" | "preview" | "split">("write");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [lightboxData, setLightboxData] = useState<{
    urls: string[];
    index: number;
  } | null>(null);

  // Auto-grow textarea height in write/split mode
  useEffect(() => {
    const el = textareaRef.current;
    if (!el || !isEditMode || notesTab === "preview") return;
    el.style.height = "auto";
    el.style.height = `${Math.max(400, el.scrollHeight)}px`;
  }, [notes, isEditMode, notesTab, mobilePane]);

  // ── Queries & Mutations ────────────────────────────────────────────────────
  const { data: marketIndexes } = useMarketIndexes();
  const activeIndexes = (marketIndexes ?? []).filter((idx) => idx.is_active);

  const { data: annotationDefinitions } = useGetAnnotationDefinitions("checkins");
  const checkinAnnotationDefs = (annotationDefinitions ?? []).filter(
    (d) => !d.is_archived && (d.scope === "checkins" || d.scope === "both")
  );

  const { data: taxonomies } = useGetTaxonomies("checkins");
  const checkinTaxonomies = (taxonomies ?? []).filter((t) => !t.is_archived);

  const assignTaxonomyMutation = useAssignCheckinTaxonomy();
  const removeTaxonomyMutation = useRemoveCheckinTaxonomy();

  const assignedTagIds = new Set((entry?.taxonomies ?? []).map((t) => t.id));

  const addNewsLink = () => {
    let trimmed = newsLink.trim();
    if (!trimmed) return;
    if (!/^https?:\/\//i.test(trimmed)) {
      trimmed = `https://${trimmed}`;
    }
    if (!newsLinks.includes(trimmed)) {
      setNewsLinks((prev) => [...prev, trimmed]);
      setNewsLink("");
    }
  };

  const removeNewsLink = (idx: number) => {
    setNewsLinks((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleToggleTag = useCallback(
    async (taxonomyId: string) => {
      if (!isEditMode) return;
      if (isNew) {
        setBufferedTagIds((prev) =>
          prev.includes(taxonomyId)
            ? prev.filter((id) => id !== taxonomyId)
            : [...prev, taxonomyId]
        );
        return;
      }
      if (!entry) return;
      if (assignedTagIds.has(taxonomyId)) {
        await removeTaxonomyMutation.mutateAsync({
          checkinId: entry.id,
          taxonomyId,
        });
      } else {
        await assignTaxonomyMutation.mutateAsync({
          checkinId: entry.id,
          taxonomyId,
        });
      }
    },
    [
      isEditMode,
      isNew,
      entry,
      assignedTagIds,
      assignTaxonomyMutation,
      removeTaxonomyMutation,
    ]
  );

  const performSave = useCallback(
    async (closeAfterSave: boolean) => {
      const showNotes = notes || null;
      const options: CheckinSaveOptions = {
        bufferedTagIds,
        bufferedAnnotations,
        closeAfterSave,
      };

      try {
        if (isNew) {
          const payload: DailyCheckinCreate = {
            date,
            target_index_ids: targetIndexIds,
            notes: showNotes,
            news_links: newsLinks.length > 0 ? newsLinks : undefined,
            screenshot_urls: screenshotKeys.length > 0 ? screenshotKeys : undefined,
          };
          await onSave(payload, options);
        } else {
          const payload: DailyCheckinUpdate = {
            target_index_ids: targetIndexIds,
            notes: showNotes,
            news_links: newsLinks,
            screenshot_urls: screenshotKeys,
          };
          await onSave(payload, options);
        }

        setBufferedTagIds([]);
        setBufferedAnnotations({});

        if (closeAfterSave) {
          setIsEditMode(false);
          router.replace(`/dashboard/checkins/${date}`);
        } else {
          router.replace(`/dashboard/checkins/${date}?edit=true`);
        }
      } catch {
        // Error state is handled by parent mutation
      }
    },
    [
      notes,
      bufferedTagIds,
      bufferedAnnotations,
      isNew,
      date,
      targetIndexIds,
      newsLinks,
      screenshotKeys,
      onSave,
      router,
    ]
  );

  // Keyboard shortcut (Cmd/Ctrl + S) — saves and stays in edit mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (isEditMode && !isSaving) {
          void performSave(false);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [performSave, isEditMode, isSaving]);

  const handleCancelEdit = useCallback(() => {
    if (entry) {
      setTargetIndexIds(entry.target_indices?.map((idx) => idx.id) ?? []);
      setNotes(entry.notes ?? "");
      setNewsLinks(entry.news_links ?? []);
      setScreenshotKeys(entry.screenshot_keys ?? []);
      setScreenshotPreviews(entry.screenshot_urls ?? []);
      setIsEditMode(false);
      router.replace(`/dashboard/checkins/${date}`);
    } else {
      router.push("/dashboard/checkins");
    }
  }, [entry, router, date]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void performSave(false);
  };

  const visibleTagIds = isNew ? bufferedTagIds : Array.from(assignedTagIds);
  const activeAnnotationsCount = isNew
    ? Object.values(bufferedAnnotations).filter((v) => v !== null && v !== undefined).length
    : (entry?.annotations ?? []).length;
  const detailsCount =
    visibleTagIds.length +
    activeAnnotationsCount +
    screenshotKeys.length +
    newsLinks.length;

  const renderMarkdownPreview = () => (
    <div className="min-h-[240px]">
      {notes.trim() ? (
        <div className="prose prose-sm sm:prose-base max-w-none text-foreground [&_a]:text-primary [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre]:bg-secondary [&_pre]:p-4 [&_pre]:rounded-lg [&_blockquote]:border-l-4 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_table]:w-full [&_th]:text-left [&_th]:border-b [&_th]:border-border [&_th]:pb-2 [&_td]:border-b [&_td]:border-border [&_td]:py-2">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
          >
            {notes}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic py-8">
          {isEditMode
            ? "Nothing to preview yet. Write your market notes in Markdown."
            : "No notes added."}
        </p>
      )}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4 pb-8">
      {/* ── Header Card (2 Rows) ────────────────────────────────────────────── */}
      <div className="solid-card p-4 sm:p-5 space-y-3">
        {/* Row 1: Back, Date + Entry Navigation (< Prev / Next >), Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <Link
              href="/dashboard/checkins"
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60 transition-colors shrink-0"
              title="Back to Timeline"
              aria-label="Back to Timeline"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>

            {/* Previous existing entry button */}
            <button
              type="button"
              disabled={!prevEntryDate}
              onClick={() => {
                if (prevEntryDate) router.push(`/dashboard/checkins/${prevEntryDate}`);
              }}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60 transition-colors disabled:opacity-35 disabled:cursor-not-allowed shrink-0"
              title={
                prevEntryDate
                  ? `Previous entry (${prevEntryDate})`
                  : "No earlier check-in entry"
              }
              aria-label="Previous Entry"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <div className="min-w-0">
              <h1 className="text-lg sm:text-xl font-bold text-foreground truncate">
                {format(new Date(`${date}T12:00:00Z`), "MMMM d, yyyy")}
              </h1>
            </div>

            {/* Next existing entry button */}
            <button
              type="button"
              disabled={!nextEntryDate}
              onClick={() => {
                if (nextEntryDate) router.push(`/dashboard/checkins/${nextEntryDate}`);
              }}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60 transition-colors disabled:opacity-35 disabled:cursor-not-allowed shrink-0"
              title={
                nextEntryDate
                  ? `Next entry (${nextEntryDate})`
                  : "No later check-in entry"
              }
              aria-label="Next Entry"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Primary Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {isEditMode ? (
              <>
                {!isNew && (
                  <button
                    type="button"
                    onClick={onDelete}
                    disabled={isDeleting || isSaving}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10 border border-destructive/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    <span className="hidden sm:inline">Delete</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                  className="px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary border border-border rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-sm font-medium bg-secondary hover:bg-muted text-foreground border border-border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {isSaving ? "Saving…" : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => void performSave(true)}
                  disabled={isSaving}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {isSaving ? "Saving…" : "Save & Close"}
                </button>
              </>
            ) : (
              <>
                {!isNew && (
                  <button
                    type="button"
                    onClick={onDelete}
                    disabled={isDeleting}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10 border border-destructive/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                    Delete
                  </button>
                )}
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    setIsEditMode(true);
                  }}
                  className="inline-flex items-center gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit Check-in
                </button>
              </>
            )}
          </div>
        </div>

        {/* Row 2: Compact Meta Bar (Target Market Indexes + Updated timestamp) */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border/60 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider mr-1">
              Target Market Indexes
            </span>
            {activeIndexes.map((idx) => {
              const selected = targetIndexIds.includes(idx.id);
              if (!isEditMode && !selected) return null;

              if (!isEditMode && selected && idx.tradingview_url) {
                return (
                  <a
                    key={idx.id}
                    href={idx.tradingview_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/25 hover:bg-primary/20 transition-colors"
                    title={`Open ${idx.name} chart on TradingView`}
                  >
                    <span>{idx.symbol}</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                );
              }

              return (
                <button
                  key={idx.id}
                  type="button"
                  disabled={!isEditMode}
                  onClick={() => {
                    setTargetIndexIds((prev) =>
                      selected
                        ? prev.filter((id) => id !== idx.id)
                        : [...prev, idx.id]
                    );
                  }}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors disabled:cursor-default ${
                    selected
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-transparent text-muted-foreground border-border hover:text-foreground hover:bg-muted/50"
                  }`}
                  title={idx.name}
                >
                  {idx.symbol}
                </button>
              );
            })}
            {!isEditMode && targetIndexIds.length === 0 && (
              <span className="text-xs text-muted-foreground italic">
                No targets selected
              </span>
            )}
          </div>

          {entry?.updated_at && (
            <span className="text-xs text-muted-foreground">
              Updated {new Date(entry.updated_at).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* ── Mobile Pane Switcher (< lg) ─────────────────────────────────────── */}
      <div
        className="flex lg:hidden p-1 rounded-xl bg-secondary border border-border"
        role="tablist"
        aria-label="Check-in view sections"
      >
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "document"}
          onClick={() => setMobilePane("document")}
          className={`flex-1 inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
            mobilePane === "document"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="w-4 h-4" />
          Document
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "details"}
          onClick={() => setMobilePane("details")}
          className={`flex-1 inline-flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
            mobilePane === "details"
              ? "bg-card text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Paperclip className="w-4 h-4" />
          Details & Media
          {detailsCount > 0 && (
            <span className="px-1.5 py-0.5 text-[11px] rounded-full bg-primary/15 text-primary font-semibold">
              {detailsCount}
            </span>
          )}
        </button>
      </div>

      {/* ── Main 2-Column Body (Left: Markdown Main Pane, Right: Side Pane) ── */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* ── Left Main Pane: Market Notes (flex-1) ─────────────────────────── */}
        <div
          className={`flex-1 min-w-0 w-full ${
            mobilePane === "document" ? "block" : "hidden lg:block"
          }`}
        >
          <div className="solid-card overflow-hidden">
            {/* Card Header */}
            <div className="flex items-center justify-between gap-4 px-5 py-3.5 border-b border-border bg-muted/20">
              <label className="text-sm font-semibold text-foreground">
                Notes
              </label>

              {isEditMode && (
                <div className="flex items-center bg-secondary p-0.5 rounded-lg border border-border">
                  <button
                    type="button"
                    onClick={() => setNotesTab("write")}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      notesTab === "write"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Write
                  </button>
                  <button
                    type="button"
                    onClick={() => setNotesTab("preview")}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      notesTab === "preview"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Preview
                  </button>
                  <button
                    type="button"
                    onClick={() => setNotesTab("split")}
                    className={`hidden lg:inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      notesTab === "split"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Columns className="w-3.5 h-3.5" />
                    Split
                  </button>
                </div>
              )}
            </div>

            {/* Card Body */}
            <div className="p-5 sm:p-6">
              {!isEditMode || notesTab === "preview" ? (
                renderMarkdownPreview()
              ) : notesTab === "split" ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                  <textarea
                    ref={textareaRef}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="How did the market feel today? Any macro events? Psychological state?"
                    aria-label="Market notes (Markdown)"
                    className="w-full min-h-[400px] resize-y rounded-lg border border-border bg-background p-4 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                  />
                  <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[400px]">
                    {renderMarkdownPreview()}
                  </div>
                </div>
              ) : (
                <textarea
                  ref={textareaRef}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="How did the market feel today? Any macro events? Psychological state?"
                  aria-label="Market notes (Markdown)"
                  className="w-full min-h-[400px] resize-y rounded-lg border border-border bg-background p-4 font-mono text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                />
              )}
            </div>
          </div>
        </div>

        {/* ── Right Side Pane (Tags & Annotations, Screenshots, News Links) ─── */}
        <aside
          className={`w-full lg:w-[360px] xl:w-[420px] shrink-0 flex-col gap-4 ${
            mobilePane === "details" ? "flex" : "hidden lg:flex"
          }`}
        >
          {/* 1. Tags & Annotations Card */}
          <section className="solid-card p-4 space-y-4">
            {/* Tags */}
            <div>
              <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2.5 flex items-center justify-between">
                <span>Tags</span>
                {visibleTagIds.length > 0 && (
                  <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                    {visibleTagIds.length}
                  </span>
                )}
              </label>

              {checkinTaxonomies.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {checkinTaxonomies.map((tag) => {
                    const isActive = visibleTagIds.includes(tag.id);
                    if (!isEditMode && !isActive) return null;
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        disabled={!isEditMode}
                        onClick={() => void handleToggleTag(tag.id)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-colors disabled:cursor-default"
                        style={{
                          backgroundColor: isActive
                            ? (tag.color_hex ?? "#888") + "20"
                            : "transparent",
                          color: isActive
                            ? (tag.color_hex ?? "#888")
                            : "var(--muted-foreground)",
                          borderColor: isActive
                            ? (tag.color_hex ?? "#888") + "40"
                            : "var(--border)",
                          borderWidth: 1,
                        }}
                      >
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{
                            backgroundColor: isActive
                              ? (tag.color_hex ?? "#888")
                              : "var(--muted-foreground)",
                          }}
                        />
                        {tag.name}
                      </button>
                    );
                  })}
                  {!isEditMode && visibleTagIds.length === 0 && (
                    <span className="text-xs text-muted-foreground italic">
                      No tags assigned
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-xs text-muted-foreground italic">
                  No tags configured
                </span>
              )}
            </div>

            {/* Annotations */}
            {checkinAnnotationDefs.length > 0 && (
              <div className="pt-3 border-t border-border/60">
                <label className="block text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3">
                  Annotations
                </label>
                <AnnotationEditor
                  checkinId={isNew ? null : (entry?.id ?? null)}
                  definitions={checkinAnnotationDefs}
                  assigned={entry?.annotations ?? []}
                  onBufferChange={(defId, value) =>
                    setBufferedAnnotations((prev) => ({
                      ...prev,
                      [defId]: value,
                    }))
                  }
                  buffered={isNew ? bufferedAnnotations : undefined}
                  isEditMode={isEditMode}
                />
              </div>
            )}
          </section>

          {/* 2. Screenshots Card (16:9 Chart Thumbnails) */}
          <section className="solid-card p-4">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center justify-between">
              <span>Screenshots</span>
              {screenshotKeys.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {screenshotKeys.length}
                </span>
              )}
            </label>

            {isEditMode && (
              <div className="mb-3">
                <ScreenshotUploader
                  onUploaded={(storageRef, previewUrl) => {
                    setScreenshotKeys((prev) => [...prev, storageRef]);
                    setScreenshotPreviews((prev) => [...prev, previewUrl]);
                  }}
                />
              </div>
            )}

            {screenshotKeys.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {screenshotKeys.map((_, i) => (
                  <div
                    key={i}
                    className="group relative aspect-video w-full rounded-lg overflow-hidden border border-border bg-secondary/60"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={resolveStorageUrl(screenshotPreviews[i])}
                      alt={`Screenshot ${i + 1}`}
                      className="w-full h-full object-cover cursor-pointer group-hover:scale-105 transition-transform duration-200"
                      onClick={() =>
                        setLightboxData({
                          urls: screenshotPreviews.map(resolveStorageUrl),
                          index: i,
                        })
                      }
                    />
                    {isEditMode && (
                      <button
                        type="button"
                        onClick={() => {
                          setScreenshotKeys((prev) =>
                            prev.filter((_, idx) => idx !== i)
                          );
                          setScreenshotPreviews((prev) =>
                            prev.filter((_, idx) => idx !== i)
                          );
                        }}
                        className="absolute top-1.5 right-1.5 bg-background/85 hover:bg-destructive hover:text-destructive-foreground text-foreground p-1 rounded-md opacity-0 group-hover:opacity-100 transition-all shadow-sm"
                        aria-label="Remove screenshot"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              !isEditMode && (
                <span className="text-xs text-muted-foreground italic">
                  No screenshots attached
                </span>
              )
            )}
          </section>

          {/* 3. News Links Card */}
          <section className="solid-card p-4">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center justify-between">
              <span>News Links</span>
              {newsLinks.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {newsLinks.length}
                </span>
              )}
            </label>

            {newsLinks.length > 0 ? (
              <div className={isEditMode ? "space-y-1.5 mb-3" : "space-y-1.5"}>
                {newsLinks.map((link, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 bg-secondary border border-border rounded-lg px-2.5 py-1.5 text-xs"
                  >
                    <Link2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:underline truncate flex-1"
                      title={link}
                    >
                      {link}
                    </a>
                    {isEditMode && (
                      <button
                        type="button"
                        onClick={() => removeNewsLink(i)}
                        className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
                        aria-label="Remove news link"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              !isEditMode && (
                <span className="text-xs text-muted-foreground italic">
                  No links added
                </span>
              )
            )}

            {isEditMode && (
              <div className="flex gap-1.5">
                <input
                  type="url"
                  value={newsLink}
                  onChange={(e) => setNewsLink(e.target.value)}
                  placeholder="https://..."
                  className="flex-1 rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addNewsLink();
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={addNewsLink}
                  disabled={!newsLink.trim()}
                  className="px-2.5 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                  aria-label="Add news link"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
            )}
          </section>
        </aside>
      </div>

      {lightboxData && (
        <CheckinLightbox
          urls={lightboxData.urls}
          initialIndex={lightboxData.index}
          onClose={() => setLightboxData(null)}
        />
      )}
    </form>
  );
}
