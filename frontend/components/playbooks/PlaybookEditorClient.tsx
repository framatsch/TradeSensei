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
 * PlaybookEditorClient — full-width split-pane editor for a single playbook.
 * Left pane (35%): tags, images, external links.
 * Right pane (65%): markdown editor with write/preview toggle.
 */

"use client";

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { ArrowLeft, X, Plus, ExternalLink, Trash2, Eye, Edit3 } from "lucide-react";
import { toast } from "react-hot-toast";
import { Spinner } from "@/components/ui/Spinner";
import { usePlaybooks, useUpdatePlaybook, useDeletePlaybook } from "@/hooks/usePlaybooks";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import {
  usePlaybookTaxonomies,
  useAssignPlaybookTaxonomy,
  useRemovePlaybookTaxonomy,
  usePlaybookAttachments,
  usePlaybookImageUploadUrl,
  useRegisterPlaybookAttachment,
  useDeletePlaybookAttachment,
  usePlaybookLinks,
  useCreatePlaybookLink,
  useDeletePlaybookLink,
} from "@/hooks/usePlaybookMetadata";
import { resolveStorageUrl, storageUploadUrl } from "@/lib/storageUrl";

type PendingPlaybookAttachment = {
  tempId: string;
  filename: string;
  contentType: string;
  storageUrl: string;
  previewUrl: string;
};

interface Props {
  id: string;
}

/**
 * Returns "text-black" or "text-white" based on the perceived luminance of
 * a hex background color, to ensure WCAG AA contrast on THEME_COLORS chips.
 */
function contrastTextColor(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  // Relative luminance per WCAG 2.1
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? "text-black" : "text-white";
}

// ─── Lightbox ─────────────────────────────────────────────────────────────────

function Lightbox({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className="max-w-full max-h-full rounded-lg object-contain"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function PlaybookEditorClient({ id }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // ── Load playbook ──────────────────────────────────────────────────────────
  const { data: playbooks, isLoading: playbooksLoading } = usePlaybooks();
  const playbook = playbooks?.find((pb) => pb.id === id);

  // ── Mode state ─────────────────────────────────────────────────────────────
  const [isEditMode, setIsEditMode] = useState(searchParams.get("edit") === "true");
  const isDraftSession = searchParams.get("draft") === "true";

  // ── Toolbar state ──────────────────────────────────────────────────────────
  const [isEditingName, setIsEditingName] = useState(false);
  const [name, setName] = useState("");
  const [targetWinrate, setTargetWinrate] = useState("");
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Sync name/winrate from loaded playbook (only on first load)
  // useRef instead of useState so React 18 Strict Mode double-mount doesn't
  // reset the flag on remount, which would leave the editor blank.
  const initializedRef = useRef(false);
  useEffect(() => {
    if (playbook && !initializedRef.current) {
      initializedRef.current = true;
      setName(playbook.name);
      setTargetWinrate(
        playbook.target_winrate
          ? (Number(playbook.target_winrate) * 100).toFixed(2).replace(/\.?0+$/, "")
          : ""
      );
      setContentMarkdown(playbook.content_markdown ?? "");
    }
  }, [playbook]);

  // ── Right pane state ───────────────────────────────────────────────────────
  const [contentMarkdown, setContentMarkdown] = useState("");
  const [editorTab, setEditorTab] = useState<"write" | "preview">("write");

  // ── Mutations ──────────────────────────────────────────────────────────────
  const { mutate: updatePlaybook, isPending: isSaving } = useUpdatePlaybook();
  const { mutateAsync: deletePlaybook, isPending: isDeleting } = useDeletePlaybook();

  // ── Taxonomy section ───────────────────────────────────────────────────────
  const { data: assignedTaxonomies = [], isSuccess: taxonomiesLoaded } = usePlaybookTaxonomies(id);
  const { data: allTaxonomies = [] } = useGetTaxonomies("playbook");
  const { mutate: assignTaxonomy } = useAssignPlaybookTaxonomy();
  const { mutate: removeTaxonomy } = useRemovePlaybookTaxonomy();

  const availableTaxonomies = useMemo(
    () => allTaxonomies.filter(
      (t) => !t.is_archived && !assignedTaxonomies.some((a) => a.id === t.id)
    ),
    [allTaxonomies, assignedTaxonomies]
  );

  // ── Attachments section ────────────────────────────────────────────────────
  const { data: attachments = [], isSuccess: attachmentsLoaded } = usePlaybookAttachments(id);
  const { mutateAsync: getUploadUrl } = usePlaybookImageUploadUrl();
  const { mutateAsync: registerAttachment } = useRegisterPlaybookAttachment();
  const { mutateAsync: deleteAttachment } = useDeletePlaybookAttachment();

  const [isSyncingAttachments, setIsSyncingAttachments] = useState(false);
  const [pendingAttachmentsToAdd, setPendingAttachmentsToAdd] = useState<PendingPlaybookAttachment[]>([]);
  const [pendingAttachmentIdsToDelete, setPendingAttachmentIdsToDelete] = useState<string[]>([]);

  const visibleAttachments = useMemo(() => {
    const persisted = attachments
      .filter((att) => !pendingAttachmentIdsToDelete.includes(att.id))
      .map((att) => ({ ...att, isPending: false }));

    const staged = pendingAttachmentsToAdd.map((att) => ({
      id: att.tempId,
      filename: att.filename,
      storage_url: att.previewUrl,
      isPending: true,
    }));

    return [...persisted, ...staged];
  }, [attachments, pendingAttachmentIdsToDelete, pendingAttachmentsToAdd]);

  const syncAttachmentChanges = useCallback(async () => {
    if (pendingAttachmentsToAdd.length === 0 && pendingAttachmentIdsToDelete.length === 0) {
      return;
    }

    setIsSyncingAttachments(true);
    try {
      for (const pending of pendingAttachmentsToAdd) {
        await registerAttachment({
          playbookId: id,
          filename: pending.filename,
          contentType: pending.contentType,
          storageUrl: pending.storageUrl,
        });
      }

      for (const attachmentId of pendingAttachmentIdsToDelete) {
        await deleteAttachment({ playbookId: id, attachmentId });
      }

      setPendingAttachmentsToAdd((prev) => {
        for (const pending of prev) {
          URL.revokeObjectURL(pending.previewUrl);
        }
        return [];
      });
      setPendingAttachmentIdsToDelete([]);
    } finally {
      setIsSyncingAttachments(false);
    }
  }, [deleteAttachment, id, pendingAttachmentIdsToDelete, pendingAttachmentsToAdd, registerAttachment]);

  const handleSave = useCallback(() => {
    const payload: { name?: string; content_markdown?: string | null; target_winrate?: number | null } = {
      name: name.trim() || playbook?.name,
      content_markdown: contentMarkdown,
    };
    if (targetWinrate.trim()) {
      const parsed = parseFloat(targetWinrate);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 100) {
        payload.target_winrate = parsed / 100;
      }
    } else {
      payload.target_winrate = null;
    }
    updatePlaybook(
      { id, payload },
      {
        onSuccess: async () => {
          try {
            await syncAttachmentChanges();
          } catch {
            toast.error("Playbook saved, but image changes failed. Please save again.");
            return;
          }
          router.replace(`/dashboard/library/playbooks/${id}?edit=true`);
          setIsEditMode(false);
          toast.success("Playbook saved");
        },
        onError: (err) => toast.error(err.message || "Failed to save playbook"),
      }
    );
  }, [name, playbook?.name, contentMarkdown, targetWinrate, updatePlaybook, id, router, syncAttachmentChanges]);

  // Keyboard shortcut (Cmd/Ctrl + S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSave]);

  // ── Links section ──────────────────────────────────────────────────────────
  const { data: links = [], isSuccess: linksLoaded } = usePlaybookLinks(id);
  const { mutate: createLink, isPending: isCreatingLink } = useCreatePlaybookLink();
  const { mutate: deleteLink } = useDeletePlaybookLink();

  const taxonomiesEverLoaded = useRef(false);
  const attachmentsEverLoaded = useRef(false);
  const linksEverLoaded = useRef(false);
  useEffect(() => { if (taxonomiesLoaded) taxonomiesEverLoaded.current = true; }, [taxonomiesLoaded]);
  useEffect(() => { if (attachmentsLoaded) attachmentsEverLoaded.current = true; }, [attachmentsLoaded]);
  useEffect(() => { if (linksLoaded) linksEverLoaded.current = true; }, [linksLoaded]);

  const handleBack = useCallback(async () => {
    // Auto-cleanup if completely empty (draft abandoned).
    // Guard 1: initializedRef — playbook data must have loaded at least once.
    // Guard 2: all sibling queries (taxonomies, attachments, links) must be
    //   loaded (isSuccess) — otherwise their data defaults to [] and we'd incorrectly
    //   delete a non-empty playbook during the in-flight window.
    const allLoaded =
      (taxonomiesLoaded || taxonomiesEverLoaded.current) &&
      (attachmentsLoaded || attachmentsEverLoaded.current) &&
      (linksLoaded || linksEverLoaded.current);
    const UNTITLED_DRAFT_NAME_PATTERN = /^Untitled Playbook(?: \d+)?$/;
    const effectiveName = name.trim() || playbook?.name || "";
    const isAutoDraftName = UNTITLED_DRAFT_NAME_PATTERN.test(effectiveName);
    const isNameUnchanged = effectiveName === playbook?.name;
    const isContentEmpty = !contentMarkdown.trim();
    const hasNoAttachments = visibleAttachments.length === 0;
    const hasNoTags = assignedTaxonomies.length === 0;
    const hasNoLinks = links.length === 0;

    if (isDraftSession && initializedRef.current && allLoaded && isAutoDraftName && isNameUnchanged && isContentEmpty && hasNoAttachments && hasNoTags && hasNoLinks) {
      try {
        await deletePlaybook(id);
      } catch {
        toast("Couldn't clean up draft — please delete it manually.", { icon: "ℹ️" });
      }
    }
    router.push("/dashboard/library/playbooks");
  }, [
    isDraftSession,
    taxonomiesLoaded,
    attachmentsLoaded,
    linksLoaded,
    name,
    contentMarkdown,
    visibleAttachments.length,
    assignedTaxonomies,
    links,
    deletePlaybook,
    id,
    router,
  ]);

  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [pasteHint, setPasteHint] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [lightboxAlt, setLightboxAlt] = useState("");

  const handleFiles = useCallback(
    async (files: FileList | File[] | null) => {
      if (!files || files.length === 0) return;
      const validFiles = Array.from(files).filter((f) => f.type.startsWith("image/"));
      if (validFiles.length === 0) return;

      setIsUploading(true);
      setUploadError(null);

      try {
        for (const file of validFiles) {
          if (file.size > 20 * 1024 * 1024) {
            setUploadError(`${file.name} is too large (max 20 MB)`);
            continue;
          }
          const { upload_url, key } = await getUploadUrl({
            playbookId: id,
            filename: file.name,
            contentType: file.type,
          });
          const res = await fetch(storageUploadUrl(upload_url), {
            method: "PUT",
            body: file,
            headers: { "Content-Type": file.type },
          });
          if (!res.ok) {
            setUploadError("Upload failed — please try again");
            continue;
          }
          setPendingAttachmentsToAdd((prev) => [
            ...prev,
            {
              tempId: crypto.randomUUID(),
              filename: file.name,
              contentType: file.type,
              storageUrl: key,
              previewUrl: URL.createObjectURL(file),
            },
          ]);
        }
      } catch {
        setUploadError("An unexpected error occurred");
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [id, getUploadUrl]
  );

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
        void handleFiles(imageFiles);
        setPasteHint(true);
        setTimeout(() => setPasteHint(false), 1500);
      }
    };
    window.addEventListener("paste", handler);
    return () => window.removeEventListener("paste", handler);
  }, [handleFiles]);

  const [linkLabel, setLinkLabel] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkError, setLinkError] = useState<string | null>(null);

  const handleAddLink = () => {
    const label = linkLabel.trim();
    const url = linkUrl.trim();
    if (!label || !url) {
      setLinkError("Both label and URL are required.");
      return;
    }
    // Block non-http(s) URLs — prevents javascript: and data: XSS vectors.
    if (!/^https?:\/\//i.test(url)) {
      setLinkError("Only http:// and https:// URLs are allowed.");
      return;
    }
    setLinkError(null);
    createLink(
      { playbookId: id, label, url },
      {
        onSuccess: () => {
          setLinkLabel("");
          setLinkUrl("");
        },
        onError: () => setLinkError("Failed to add link."),
      }
    );
  };

  // ── Ref resolver for markdown preview ─────────────────────────────────────
  // Resolved inline in the img: component override — no separate string pass needed.

  // ── Loading / not found states ─────────────────────────────────────────────
  if (playbooksLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!playbook) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-muted-foreground">Playbook not found.</p>
        <button
          onClick={() => router.push("/dashboard/library/playbooks")}
          className="px-4 py-2 text-sm bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
        >
          Back to Playbooks
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 h-full">
      {/* ── Toolbar ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-card shrink-0">
        {/* Back button */}
        <button
          onClick={handleBack}
          disabled={isDeleting}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-50"
          title="Back to playbooks"
          aria-label="Back to playbooks"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>

        {/* Inline name edit */}
        <div className="flex-1 min-w-0">
          {isEditMode && isEditingName ? (
            <input
              ref={nameInputRef}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={() => setIsEditingName(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === "Escape") setIsEditingName(false);
              }}
              className="w-full max-w-md px-2 py-1 text-base font-semibold bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              autoFocus
            />
          ) : (
            <button
              onClick={() => {
                if (!isEditMode) return;
                setIsEditingName(true);
                setTimeout(() => nameInputRef.current?.select(), 0);
              }}
              className={`text-base font-semibold text-foreground truncate max-w-md text-left ${isEditMode ? "hover:text-primary transition-colors cursor-pointer" : "cursor-default"}`}
              title={isEditMode ? "Click to edit name" : undefined}
            >
              {name || playbook.name}
            </button>
          )}
        </div>

        {/* Target win rate */}
        <div className="flex items-center gap-1.5 shrink-0">
          <label className="text-xs text-muted-foreground whitespace-nowrap">Target Win Rate</label>
          {isEditMode ? (
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={targetWinrate}
                onChange={(e) => setTargetWinrate(e.target.value)}
                placeholder="—"
                className="w-20 px-2 py-1 pr-5 text-sm font-mono bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary text-right"
              />
              <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground pointer-events-none">
                %
              </span>
            </div>
          ) : (
            <span className="text-sm font-mono text-foreground">{targetWinrate ? `${targetWinrate}%` : "—"}</span>
          )}
        </div>

        {/* Actions */}
        {isEditMode ? (
          <button
            onClick={() => {
              handleSave();
            }}
            disabled={isSaving || isSyncingAttachments}
            className="px-4 py-1.5 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0 ml-2"
          >
            {isSaving || isSyncingAttachments ? "Saving…" : "Save"}
          </button>
        ) : (
          <div className="flex items-center gap-2 ml-2">
            <button
              onClick={() => {
                if (confirm("Delete this playbook? This cannot be undone.")) {
                  deletePlaybook(id, { onSuccess: () => router.push("/dashboard/library/playbooks") });
                }
              }}
              disabled={isDeleting}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
            <button
              onClick={() => setIsEditMode(true)}
              className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors shrink-0"
            >
              <Edit3 className="w-4 h-4" />
              Edit
            </button>
          </div>
        )}
      </div>

      {/* ── Split pane ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row flex-1 min-h-0 overflow-hidden">
        {/* ── Left pane ───────────────────────────────────────────────────── */}
        <div
          className="flex flex-col gap-5 overflow-y-auto p-4 border-b lg:border-b-0 lg:border-r border-border bg-card shrink-0 w-full lg:w-[35%]"
        >
          {/* ── Tags ──────────────────────────────────────────────────────── */}
          <section>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2">
              Tags
            </h3>

            {/* Assigned chips */}
            <div className="flex flex-wrap gap-1.5 mb-2">
              {assignedTaxonomies.map((t) => (
                <span
                  key={t.id}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${contrastTextColor(t.color_hex)}`}
                  style={{ backgroundColor: t.color_hex }}
                >
                  {t.name}
                  {isEditMode && (
                    <button
                      onClick={() => removeTaxonomy({ playbookId: id, taxonomyId: t.id })}
                      className="hover:opacity-70 transition-opacity"
                      aria-label={`Remove tag ${t.name}`}
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </span>
              ))}
              {assignedTaxonomies.length === 0 && (
                <span className="text-xs text-muted-foreground italic">No tags assigned</span>
              )}
            </div>

            {/* Add tag dropdown */}
            {isEditMode && availableTaxonomies.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    assignTaxonomy({ playbookId: id, taxonomyId: e.target.value });
                    e.target.value = "";
                  }
                }}
                className="w-full px-2 py-1.5 text-sm bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">+ Add tag…</option>
                {availableTaxonomies.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            )}
          </section>

          {/* ── Images ────────────────────────────────────────────────────── */}
          <section>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2">
              Images
            </h3>

            {/* Upload zone */}
            {isEditMode && (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  void handleFiles(e.dataTransfer.files);
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 ${
                  isDragging || pasteHint
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
                  onChange={(e) => void handleFiles(e.target.files)}
                  disabled={isUploading}
                />
                {isUploading ? (
                  <span className="text-sm text-primary animate-pulse">Uploading…</span>
                ) : pasteHint ? (
                  <span className="text-sm text-primary font-medium">Pasted!</span>
                ) : (
                  <>
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      className="w-5 h-5 text-muted-foreground"
                    >
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <span className="text-xs text-muted-foreground">
                      <span className="text-primary font-medium">Click</span>, drag & drop, or{" "}
                      <kbd className="px-1 py-0.5 text-xs font-mono bg-secondary border border-border rounded">
                        ⌘V
                      </kbd>{" "}
                      to paste
                    </span>
                    <span className="text-xs text-muted-foreground">PNG, JPG, GIF, WebP · max 20 MB</span>
                  </>
                )}
              </div>
            )}
            {uploadError && (
              <p className="mt-1.5 text-xs text-destructive">{uploadError}</p>
            )}

            {/* Attachment list */}
            {visibleAttachments.length > 0 ? (
              <ul className={isEditMode ? "mt-3 space-y-1.5" : "space-y-1.5"}>
                {visibleAttachments.map((att) => (
                  <li
                    key={att.id}
                    className="flex items-center gap-2 p-1.5 rounded-lg bg-secondary border border-border"
                  >
                    <button
                      type="button"
                      onClick={() => {
                        setLightboxSrc(resolveStorageUrl(att.storage_url));
                        setLightboxAlt(att.filename);
                      }}
                      className="shrink-0"
                      aria-label={`View ${att.filename}`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={resolveStorageUrl(att.storage_url)}
                        alt={att.filename}
                        className="w-10 h-10 rounded object-cover border border-border"
                      />
                    </button>
                    <span className="flex-1 text-xs text-foreground truncate" title={att.filename}>
                      {att.filename}
                    </span>
                    {att.isPending && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded border border-primary/30 text-primary bg-primary/10">
                        Unsaved
                      </span>
                    )}
                    {isEditMode && (
                      <button
                        onClick={() => {
                          if (att.isPending) {
                            setPendingAttachmentsToAdd((prev) => {
                              const removed = prev.find((p) => p.tempId === att.id);
                              if (removed) {
                                URL.revokeObjectURL(removed.previewUrl);
                              }
                              return prev.filter((p) => p.tempId !== att.id);
                            });
                            return;
                          }
                          setPendingAttachmentIdsToDelete((prev) =>
                            prev.includes(att.id) ? prev : [...prev, att.id]
                          );
                        }}
                        className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
                        aria-label={`Delete ${att.filename}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : !isEditMode && (
              <span className="text-xs text-muted-foreground italic">No images</span>
            )}
          </section>

          {/* ── External Links ─────────────────────────────────────────────── */}
          <section>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-2 flex items-center justify-between">
              <span>External Links</span>
              {links.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {links.length}
                </span>
              )}
            </h3>

            {/* Link list */}
            {links.length > 0 ? (
              <ul className={isEditMode ? "space-y-1 mb-3" : "space-y-1"}>
                {links.map((link) => (
                  <li
                    key={link.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-secondary border border-border"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 text-xs text-primary hover:underline truncate"
                      title={link.url}
                    >
                      {link.label}
                    </a>
                    {isEditMode && (
                      <button
                        onClick={() => deleteLink({ playbookId: id, linkId: link.id })}
                        className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
                        aria-label={`Delete link ${link.label}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : !isEditMode && (
              <span className="text-xs text-muted-foreground italic">No links</span>
            )}

            {/* Add link form */}
            {isEditMode && (
              <div className="space-y-1.5 p-2 bg-secondary/50 rounded-lg border border-border/50">
                <p className="text-[11px] font-medium text-muted-foreground mb-1">Add new link</p>
                <input
                  type="text"
                  value={linkLabel}
                  onChange={(e) => setLinkLabel(e.target.value.slice(0, 200))}
                  placeholder="Label (e.g. TradingView chart)"
                  className="w-full px-2 py-1.5 text-sm bg-background border border-border rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={linkUrl}
                    onChange={(e) => setLinkUrl(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAddLink();
                    }}
                    placeholder="https://…"
                    className="flex-1 px-2 py-1.5 text-sm bg-background border border-border rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    onClick={handleAddLink}
                    disabled={isCreatingLink || !linkLabel.trim() || !linkUrl.trim()}
                    className="px-2.5 py-1.5 text-sm bg-primary hover:bg-primary/90 text-white rounded-md transition-colors disabled:opacity-50 shrink-0"
                    aria-label="Add link"
                  >
                    {isCreatingLink ? <Spinner size="sm" /> : <Plus className="w-4 h-4" />}
                  </button>
                </div>
                {linkError && <p className="text-xs text-destructive mt-1">{linkError}</p>}
              </div>
            )}
          </section>
        </div>

        {/* ── Right pane (65%) ─────────────────────────────────────────────── */}
        <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
          {/* Tab bar */}
          {isEditMode && (
            <div className="flex items-center gap-1 px-4 pt-3 pb-0 border-b border-border bg-background shrink-0">
              <button
                onClick={() => setEditorTab("write")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-t-md transition-colors border-b-2 -mb-px ${
                  editorTab === "write"
                    ? "border-primary text-foreground font-medium"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Edit3 className="w-3.5 h-3.5" />
                Write
              </button>
              <button
                onClick={() => setEditorTab("preview")}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-t-md transition-colors border-b-2 -mb-px ${
                  editorTab === "preview"
                    ? "border-primary text-foreground font-medium"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                Preview
              </button>
            </div>
          )}

          {/* Editor / Preview */}
          <div className="flex-1 min-h-0 overflow-hidden">
            {isEditMode && editorTab === "write" ? (
              <textarea
                value={contentMarkdown}
                onChange={(e) => setContentMarkdown(e.target.value)}
                placeholder="Write your detailed strategy rules here using Markdown…"
                aria-label="Playbook content (Markdown)"
                className="w-full h-full resize-none px-4 py-3 font-mono text-sm bg-background text-foreground placeholder:text-muted-foreground focus:outline-none"
                spellCheck={false}
              />
            ) : (
              <div className="h-full overflow-y-auto px-6 py-4">
                {contentMarkdown ? (
                  <div className="prose prose-sm max-w-none text-foreground [&_a]:text-primary [&_code]:bg-secondary [&_code]:px-1 [&_code]:rounded [&_pre]:bg-secondary [&_pre]:p-3 [&_pre]:rounded-lg [&_blockquote]:border-l-4 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_table]:w-full [&_th]:text-left [&_th]:border-b [&_th]:border-border [&_th]:pb-1 [&_td]:border-b [&_td]:border-border [&_td]:py-1">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeSanitize]}
                      components={{
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        img: ({ src, alt, ...rest }: any) => {
                          const resolved = src?.startsWith("ref:")
                            ? (() => {
                                const uuid = src.slice(4);
                                const found = attachments.find((a) => a.id === uuid);
                                return found ? found.storage_url : null;
                              })()
                            : src;
                          if (!resolved) {
                            return (
                              <span className="text-xs text-muted-foreground italic">
                                [attachment deleted]
                              </span>
                            );
                          }
                          // eslint-disable-next-line @next/next/no-img-element
                          return <img src={resolved} alt={alt ?? ""} {...rest} />;
                        },
                      }}
                    >
                      {contentMarkdown}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">Nothing to preview.</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Lightbox */}
      {lightboxSrc && (
        <Lightbox
          src={lightboxSrc}
          alt={lightboxAlt}
          onClose={() => setLightboxSrc(null)}
        />
      )}
    </div>
  );
}
