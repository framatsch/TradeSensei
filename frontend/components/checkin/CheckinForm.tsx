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

import { useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { type DailyCheckinRead, type DailyCheckinCreate, type DailyCheckinUpdate } from "@/lib/api/types.gen";
import { X, Link2, Loader2, Check, PlusCircle, Trash2, Edit3 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ScreenshotUploader } from "@/components/checkin/ScreenshotUploader";
import { AnnotationEditor } from "@/components/checkin/AnnotationEditor";
import { useMarketIndexes } from "@/hooks/useCheckinDefinitions";
import { useSettings } from "@/hooks/useSettings";
import { CheckinLightbox } from "@/components/checkin/CheckinLightbox";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import {
  useAssignCheckinTaxonomy,
  useRemoveCheckinTaxonomy,
} from "@/hooks/useCheckinMetadata";

export function CheckinForm({
  date,
  entry,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  date: string;
  entry: DailyCheckinRead | null | undefined;
  /** marketPhases prop removed — now handled by AnnotationEditor */
  onSave: (data: DailyCheckinCreate | DailyCheckinUpdate) => void;
  onDelete: () => void;
  isSaving: boolean;
  isDeleting: boolean;
}) {
  const [targetIndexIds, setTargetIndexIds] = useState<string[]>(
    entry?.target_indices?.map((index) => index.id) ?? []
  );
  const [notes, setNotes] = useState(entry?.notes ?? "");
  const [newsLink, setNewsLink] = useState("");
  const [newsLinks, setNewsLinks] = useState<string[]>(entry?.news_links ?? []);
  const [screenshotKeys, setScreenshotKeys] = useState<string[]>(entry?.screenshot_keys ?? []);
  const [screenshotPreviews, setScreenshotPreviews] = useState<string[]>(entry?.screenshot_urls ?? []);

  // Buffered annotations + tags for new (not-yet-created) check-ins
  const [bufferedAnnotations, setBufferedAnnotations] = useState<Record<string, unknown>>({});
  const [bufferedTagIds, setBufferedTagIds] = useState<string[]>([]);

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

  const assignedTagIds = new Set(
    (entry?.taxonomies ?? []).map((t) => t.id)
  );

  const [notesTab, setNotesTab] = useState<"write" | "preview">("write");
  const searchParams = useSearchParams();
  const isNew = !entry;
  const [isEditMode, setIsEditMode] = useState(isNew || searchParams.get("edit") === "true");
  const [lightboxData, setLightboxData] = useState<{ urls: string[]; index: number } | null>(null);

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
        // Buffer for new check-in
        setBufferedTagIds((prev) =>
          prev.includes(taxonomyId) ? prev.filter((id) => id !== taxonomyId) : [...prev, taxonomyId]
        );
        return;
      }
      if (!entry) return;
      if (assignedTagIds.has(taxonomyId)) {
        await removeTaxonomyMutation.mutateAsync({ checkinId: entry.id, taxonomyId });
      } else {
        await assignTaxonomyMutation.mutateAsync({ checkinId: entry.id, taxonomyId });
      }
    },
    [isEditMode, isNew, entry, assignedTagIds, assignTaxonomyMutation, removeTaxonomyMutation]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const showNotes = notes || null;

    if (isNew) {
      const payload: DailyCheckinCreate = {
        date,
        target_index_ids: targetIndexIds,
        notes: showNotes,
        news_links: newsLinks.length > 0 ? newsLinks : undefined,
        screenshot_urls: screenshotKeys.length > 0 ? screenshotKeys : undefined,
      };
      onSave(payload);
    } else {
      const payload: DailyCheckinUpdate = {
        target_index_ids: targetIndexIds,
        notes: showNotes,
        news_links: newsLinks,
        screenshot_urls: screenshotKeys,
      };
      onSave(payload);
    }
  };

  const visibleTagIds = isNew ? bufferedTagIds : Array.from(assignedTagIds);

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Tags */}
      {checkinTaxonomies.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-foreground mb-2">
            Tags
          </label>
          <div className="flex flex-wrap gap-2">
            {checkinTaxonomies.map((tag) => {
              const isActive = visibleTagIds.includes(tag.id);
              if (!isEditMode && !isActive) return null;
              return (
                <button
                  key={tag.id}
                  type="button"
                  disabled={!isEditMode}
                  onClick={() => void handleToggleTag(tag.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors disabled:cursor-default"
                  style={{
                    backgroundColor: isActive ? (tag.color_hex ?? "#888") + "20" : "transparent",
                    color: isActive ? (tag.color_hex ?? "#888") : "var(--muted-foreground)",
                    borderColor: isActive ? (tag.color_hex ?? "#888") + "40" : "var(--border)",
                    borderWidth: 1,
                  }}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: isActive ? (tag.color_hex ?? "#888") : "var(--muted-foreground)" }}
                  />
                  {tag.name}
                </button>
              );
            })}
            {!isEditMode && visibleTagIds.length === 0 && (
              <span className="text-sm text-muted-foreground italic">No tags assigned</span>
            )}
          </div>
        </div>
      )}

      {/* Annotations */}
      {checkinAnnotationDefs.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-foreground mb-3">
            Annotations
          </label>
          <AnnotationEditor
            checkinId={isNew ? null : (entry?.id ?? null)}
            definitions={checkinAnnotationDefs}
            assigned={entry?.annotations ?? []}
            onBufferChange={(defId, value) =>
              setBufferedAnnotations((prev) => ({ ...prev, [defId]: value }))
            }
            buffered={isNew ? bufferedAnnotations : undefined}
            isEditMode={isEditMode}
          />
        </div>
      )}

      {/* Target Market Indexes */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Target Market Indexes
        </label>
        <div className="flex flex-wrap gap-2">
          {activeIndexes.map((idx) => {
            const selected = targetIndexIds.includes(idx.id);
            if (!isEditMode && !selected) return null;
            return (
              <button
                key={idx.id}
                type="button"
                disabled={!isEditMode}
                onClick={() => {
                  setTargetIndexIds((prev) =>
                    selected ? prev.filter((id) => id !== idx.id) : [...prev, idx.id]
                  );
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors disabled:cursor-default ${
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
            <span className="text-sm text-muted-foreground italic">No targets selected</span>
          )}
        </div>
      </div>

      {/* Notes */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-foreground">
            Notes
          </label>
          {isEditMode && (
            <div className="flex bg-muted/50 p-0.5 rounded-lg border border-border">
              <button
                type="button"
                onClick={() => setNotesTab("write")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  notesTab === "write"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Write
              </button>
              <button
                type="button"
                onClick={() => setNotesTab("preview")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                  notesTab === "preview"
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Preview
              </button>
            </div>
          )}
        </div>
        {isEditMode && notesTab === "write" ? (
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={6}
            placeholder="How did the market feel today? Any macro events? Psychological state?"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-[color-mix(in_srgb,var(--primary)_20%,transparent)] focus:border-primary transition-colors resize-y"
          />
        ) : (
          <div className="w-full rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-foreground min-h-[148px] prose prose-sm max-w-none">
            {notes.trim() ? (
              <ReactMarkdown>{notes}</ReactMarkdown>
            ) : (
              <span className="text-muted-foreground/50 italic">No notes added.</span>
            )}
          </div>
        )}
      </div>

      {/* Screenshots */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Screenshots
        </label>
        {screenshotKeys.length > 0 ? (
          <div className="flex flex-wrap gap-3 mb-3">
            {screenshotKeys.map((_, i) => (
              <div key={i} className="relative group w-32 h-20 rounded-md overflow-hidden border border-border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={screenshotPreviews[i]}
                  alt={`Screenshot ${i + 1}`}
                  className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => setLightboxData({ urls: screenshotPreviews, index: i })}
                />
                {isEditMode && (
                  <button
                    type="button"
                    onClick={() => {
                      setScreenshotKeys((prev) => prev.filter((_, idx) => idx !== i));
                      setScreenshotPreviews((prev) => prev.filter((_, idx) => idx !== i));
                    }}
                    className="absolute top-1 right-1 bg-background/80 hover:bg-destructive hover:text-destructive-foreground text-foreground p-1 rounded-sm opacity-0 group-hover:opacity-100 transition-all"
                    aria-label="Remove screenshot"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : !isEditMode && (
          <span className="text-sm text-muted-foreground italic">No screenshots attached</span>
        )}
        {isEditMode && (
          <ScreenshotUploader
            onUploaded={(storageRef, previewUrl) => {
              setScreenshotKeys((prev) => [...prev, storageRef]);
              setScreenshotPreviews((prev) => [...prev, previewUrl]);
            }}
          />
        )}
      </div>

      {/* News Links */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          News Links
        </label>
        {newsLinks.length > 0 ? (
          <div className="space-y-1 mb-3">
            {newsLinks.map((link, i) => (
              <div
                key={i}
                className="flex items-center gap-2 bg-muted/40 rounded-md px-3 py-1.5 text-sm"
              >
                <Link2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <a
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline truncate flex-1"
                >
                  {link}
                </a>
                {isEditMode && (
                  <button
                    type="button"
                    onClick={() => removeNewsLink(i)}
                    className="text-muted-foreground hover:text-destructive shrink-0"
                    aria-label="Remove news link"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : !isEditMode && (
          <span className="text-sm text-muted-foreground italic">No links added</span>
        )}
        {isEditMode && (
          <div className="flex gap-2">
            <input
              type="url"
              value={newsLink}
              onChange={(e) => setNewsLink(e.target.value)}
              placeholder="https://..."
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-[color-mix(in_srgb,var(--primary)_20%,transparent)] focus:border-primary transition-colors"
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
              className="px-3 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <PlusCircle className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2 border-t border-border">
        {isEditMode ? (
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            {isNew ? "Create Check-in" : "Save Changes"}
          </button>
        ) : (
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              setIsEditMode(true);
            }}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <Edit3 className="w-4 h-4" />
            Edit Check-in
          </button>
        )}
        {!isNew && (
          <button
            type="button"
            onClick={onDelete}
            disabled={isDeleting}
            className="inline-flex items-center gap-2 border border-[color-mix(in_srgb,var(--destructive)_30%,transparent)] text-destructive hover:bg-[color-mix(in_srgb,var(--destructive)_10%,transparent)] px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ml-auto"
          >
            {isDeleting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
            Delete
          </button>
        )}
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
