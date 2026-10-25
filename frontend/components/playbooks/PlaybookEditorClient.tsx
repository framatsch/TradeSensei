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
 * PlaybookEditorClient — Unified full-width document-first detail & editor view for a playbook.
 * Desktop (lg+): Header Card on top, Left Main Pane (flex-1) for Markdown documentation,
 * Right Side Pane (w-[360px] xl:w-[420px]) for Tags, 16:9 Chart Images, and External Links.
 * Mobile (< lg): Segmented switcher between "Document" and "Details & Media".
 */

"use client";

import { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import {
  ArrowLeft,
  X,
  Plus,
  ExternalLink,
  Trash2,
  Eye,
  Edit3,
  Columns,
  FileText,
  Paperclip,
  Copy,
  Check,
} from "lucide-react";
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

  // ── Mode & Mobile Pane state ───────────────────────────────────────────────
  const [isEditMode, setIsEditMode] = useState(searchParams.get("edit") === "true");
  const isDraftSession = searchParams.get("draft") === "true";
  const [mobilePane, setMobilePane] = useState<"document" | "details">("document");

  // ── Header / Form state ────────────────────────────────────────────────────
  const [isEditingName, setIsEditingName] = useState(false);
  const [name, setName] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [targetWinrate, setTargetWinrate] = useState("");
  const nameInputRef = useRef<HTMLInputElement>(null);

  // ── Document / Editor state ────────────────────────────────────────────────
  const [contentMarkdown, setContentMarkdown] = useState("");
  const [editorTab, setEditorTab] = useState<"write" | "preview" | "split">("write");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [copiedAttachmentId, setCopiedAttachmentId] = useState<string | null>(null);

  // Sync name/winrate/status from loaded playbook (only on first load)
  const initializedRef = useRef(false);
  useEffect(() => {
    if (playbook && !initializedRef.current) {
      initializedRef.current = true;
      setName(playbook.name);
      setIsActive(playbook.is_active);
      setTargetWinrate(
        playbook.target_winrate
          ? (Number(playbook.target_winrate) * 100).toFixed(2).replace(/\.?0+$/, "")
          : ""
      );
      setContentMarkdown(playbook.description ?? "");
    }
  }, [playbook]);

  // Auto-grow textarea height in write/split mode so page scrolls naturally
  useEffect(() => {
    const el = textareaRef.current;
    if (!el || !isEditMode || editorTab === "preview") return;
    el.style.height = "auto";
    el.style.height = `${Math.max(480, el.scrollHeight)}px`;
  }, [contentMarkdown, isEditMode, editorTab, mobilePane]);

  // ── Mutations ──────────────────────────────────────────────────────────────
  const { mutate: updatePlaybook, isPending: isSaving } = useUpdatePlaybook();
  const { mutateAsync: deletePlaybook, isPending: isDeleting } = useDeletePlaybook();

  // ── Taxonomy section ───────────────────────────────────────────────────────
  const { data: assignedTaxonomies = [], isSuccess: taxonomiesLoaded } = usePlaybookTaxonomies(id);
  const { data: allTaxonomies = [] } = useGetTaxonomies("playbook");
  const { mutate: assignTaxonomy } = useAssignPlaybookTaxonomy();
  const { mutate: removeTaxonomy } = useRemovePlaybookTaxonomy();

  const availableTaxonomies = useMemo(
    () =>
      allTaxonomies.filter(
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

  const handleSave = useCallback(
    (closeAfterSave = false) => {
      const payload: {
        name?: string;
        description?: string | null;
        target_winrate?: number | null;
        is_active?: boolean;
      } = {
        name: name.trim() || playbook?.name,
        description: contentMarkdown,
        is_active: isActive,
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
            if (closeAfterSave) {
              router.replace(`/dashboard/library/playbooks/${id}`);
              setIsEditMode(false);
            } else {
              router.replace(`/dashboard/library/playbooks/${id}?edit=true`);
            }
            toast.success("Playbook saved");
          },
          onError: (err) => toast.error(err.message || "Failed to save playbook"),
        }
      );
    },
    [
      name,
      playbook?.name,
      contentMarkdown,
      targetWinrate,
      isActive,
      updatePlaybook,
      id,
      router,
      syncAttachmentChanges,
    ]
  );

  // Keyboard shortcut (Cmd/Ctrl + S) — saves and stays in edit mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (isEditMode) {
          handleSave(false);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSave, isEditMode]);

  // ── Links section ──────────────────────────────────────────────────────────
  const { data: links = [], isSuccess: linksLoaded } = usePlaybookLinks(id);
  const { mutate: createLink, isPending: isCreatingLink } = useCreatePlaybookLink();
  const { mutate: deleteLink } = useDeletePlaybookLink();

  const taxonomiesEverLoaded = useRef(false);
  const attachmentsEverLoaded = useRef(false);
  const linksEverLoaded = useRef(false);
  useEffect(() => {
    if (taxonomiesLoaded) taxonomiesEverLoaded.current = true;
  }, [taxonomiesLoaded]);
  useEffect(() => {
    if (attachmentsLoaded) attachmentsEverLoaded.current = true;
  }, [attachmentsLoaded]);
  useEffect(() => {
    if (linksLoaded) linksEverLoaded.current = true;
  }, [linksLoaded]);

  const handleBack = useCallback(async () => {
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

    if (
      isDraftSession &&
      initializedRef.current &&
      allLoaded &&
      isAutoDraftName &&
      isNameUnchanged &&
      isContentEmpty &&
      hasNoAttachments &&
      hasNoTags &&
      hasNoLinks
    ) {
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
    playbook?.name,
    contentMarkdown,
    visibleAttachments.length,
    assignedTaxonomies,
    links,
    deletePlaybook,
    id,
    router,
  ]);

  const handleCancelEdit = useCallback(() => {
    if (playbook) {
      setName(playbook.name);
      setIsActive(playbook.is_active);
      setTargetWinrate(
        playbook.target_winrate
          ? (Number(playbook.target_winrate) * 100).toFixed(2).replace(/\.?0+$/, "")
          : ""
      );
      setContentMarkdown(playbook.description ?? "");
    }
    setPendingAttachmentsToAdd((prev) => {
      for (const pending of prev) {
        URL.revokeObjectURL(pending.previewUrl);
      }
      return [];
    });
    setPendingAttachmentIdsToDelete([]);
    setIsEditingName(false);
    setIsEditMode(false);
    router.replace(`/dashboard/library/playbooks/${id}`);
  }, [playbook, router, id]);

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
      if (validFiles.length === 0) {
        setUploadError("Only image files (PNG, JPG, GIF, WebP) are supported.");
        return;
      }

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
    if (!isEditMode) return;
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
  }, [handleFiles, isEditMode]);

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

  const handleInsertOrCopyImageRef = (attId: string, filename: string) => {
    const markdownSnippet = `![${filename}](ref:${attId})`;
    if (isEditMode) {
      setContentMarkdown((prev) =>
        prev.trim() ? `${prev}\n\n${markdownSnippet}` : markdownSnippet
      );
      toast.success("Image reference appended to Markdown");
    } else if (navigator.clipboard) {
      void navigator.clipboard.writeText(markdownSnippet);
      toast.success("Markdown image ref copied");
    }
    setCopiedAttachmentId(attId);
    setTimeout(() => setCopiedAttachmentId(null), 1500);
  };

  const detailsCount = assignedTaxonomies.length + visibleAttachments.length + links.length;

  const renderMarkdownPreview = () => (
    <div className="min-h-[240px]">
      {contentMarkdown.trim() ? (
        <div className="prose prose-sm sm:prose-base max-w-none text-foreground [&_a]:text-primary [&_code]:bg-secondary [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre]:bg-secondary [&_pre]:p-4 [&_pre]:rounded-lg [&_blockquote]:border-l-4 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_table]:w-full [&_th]:text-left [&_th]:border-b [&_th]:border-border [&_th]:pb-2 [&_td]:border-b [&_td]:border-border [&_td]:py-2 [&_img]:rounded-lg [&_img]:border [&_img]:border-border [&_img]:max-h-[480px] [&_img]:object-contain">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
            components={{
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              img: ({ src, alt, ...rest }: any) => {
                const resolved = src?.startsWith("ref:")
                  ? (() => {
                      const uuid = src.slice(4);
                      const found = visibleAttachments.find((a) => a.id === uuid);
                      return found ? resolveStorageUrl(found.storage_url) : null;
                    })()
                  : src;
                if (!resolved) {
                  return (
                    <span className="text-xs text-muted-foreground italic">
                      [attachment deleted]
                    </span>
                  );
                }
                return (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={resolved}
                    alt={alt ?? ""}
                    className="cursor-pointer hover:opacity-95 transition-opacity"
                    onClick={() => {
                      setLightboxSrc(resolved);
                      setLightboxAlt(alt ?? "");
                    }}
                    {...rest}
                  />
                );
              },
            }}
          >
            {contentMarkdown}
          </ReactMarkdown>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground italic py-8">
          {isEditMode
            ? "Nothing to preview yet. Start writing your strategy rules in Markdown."
            : "No strategy documentation written yet. Click Edit to add rules."}
        </p>
      )}
    </div>
  );

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
    <div className="w-full space-y-4 pb-8">
      {/* ── Header Card (2 Rows) ────────────────────────────────────────────── */}
      <div className="solid-card p-4 sm:p-5 space-y-3">
        {/* Row 1: Back, Title, Action Buttons */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <button
              onClick={() => void handleBack()}
              disabled={isDeleting}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary border border-border/60 transition-colors disabled:opacity-50 shrink-0"
              title="Back to playbooks"
              aria-label="Back to playbooks"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>

            <div className="min-w-0 flex-1">
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
                  className="w-full max-w-lg px-2.5 py-1 text-lg font-bold bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  autoFocus
                />
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    if (!isEditMode) return;
                    setIsEditingName(true);
                    setTimeout(() => nameInputRef.current?.select(), 0);
                  }}
                  className={`text-lg sm:text-xl font-bold text-foreground truncate max-w-full text-left inline-flex items-center gap-2 ${
                    isEditMode
                      ? "hover:text-primary transition-colors cursor-pointer"
                      : "cursor-default"
                  }`}
                  title={isEditMode ? "Click to edit name" : undefined}
                >
                  <span className="truncate">{name || playbook.name}</span>
                  {isEditMode && <Edit3 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />}
                </button>
              )}
            </div>
          </div>

          {/* Primary Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {isEditMode ? (
              <>
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  disabled={isSaving || isSyncingAttachments}
                  className="px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary border border-border rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handleSave(false)}
                  disabled={isSaving || isSyncingAttachments}
                  className="px-3.5 py-1.5 text-sm font-medium bg-secondary hover:bg-muted text-foreground border border-border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving || isSyncingAttachments ? "Saving…" : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => handleSave(true)}
                  disabled={isSaving || isSyncingAttachments}
                  className="px-4 py-1.5 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSaving || isSyncingAttachments ? "Saving…" : "Save & Close"}
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => {
                    if (confirm("Delete this playbook? This cannot be undone.")) {
                      void deletePlaybook(id, {
                        onSuccess: () => router.push("/dashboard/library/playbooks"),
                      });
                    }
                  }}
                  disabled={isDeleting}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive/10 border border-destructive/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-4 h-4" />
                  Delete
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditMode(true)}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors"
                >
                  <Edit3 className="w-4 h-4" />
                  Edit
                </button>
              </>
            )}
          </div>
        </div>

        {/* Row 2: Compact Meta Bar (Status + Target Win Rate) */}
        <div className="flex flex-wrap items-center gap-4 pt-3 border-t border-border/60 text-sm">
          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Status
            </span>
            {isEditMode ? (
              <button
                type="button"
                onClick={() => setIsActive((prev) => !prev)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors ${
                  isActive
                    ? "bg-success/10 text-success border-success/30 hover:bg-success/20"
                    : "bg-secondary text-muted-foreground border-border hover:bg-muted"
                }`}
                aria-label={`Toggle active status, currently ${isActive ? "Active" : "Inactive"}`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isActive ? "bg-success" : "bg-muted-foreground"
                  }`}
                />
                {isActive ? "Active" : "Inactive"}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  const nextStatus = !playbook?.is_active;
                  updatePlaybook(
                    { id, payload: { is_active: nextStatus } },
                    {
                      onSuccess: () => {
                        setIsActive(nextStatus);
                        toast.success(`Playbook marked as ${nextStatus ? "Active" : "Inactive"}`);
                      },
                      onError: (err) => toast.error(err.message || "Failed to update status"),
                    }
                  );
                }}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer ${
                  playbook?.is_active
                    ? "bg-success/10 text-success border-success/30 hover:bg-success/20"
                    : "bg-secondary text-muted-foreground border-border hover:bg-muted"
                }`}
                title="Click to toggle status"
                aria-label={`Toggle active status, currently ${
                  playbook?.is_active ? "Active" : "Inactive"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    playbook?.is_active ? "bg-success" : "bg-muted-foreground"
                  }`}
                />
                {playbook?.is_active ? "Active" : "Inactive"}
              </button>
            )}
          </div>

          <div className="h-4 w-px bg-border hidden sm:block" />

          {/* Target Win Rate */}
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider whitespace-nowrap">
              Target Win Rate
            </label>
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
                  className="w-24 px-2.5 py-1 pr-6 text-sm font-mono bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary text-right"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground pointer-events-none">
                  %
                </span>
              </div>
            ) : (
              <span className="text-sm font-mono font-semibold text-foreground">
                {targetWinrate ? `${targetWinrate}%` : "—"}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* ── Mobile Pane Switcher (< lg) ─────────────────────────────────────── */}
      <div
        className="flex lg:hidden p-1 rounded-xl bg-secondary border border-border"
        role="tablist"
        aria-label="Playbook view sections"
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
        {/* ── Left Main Pane: Strategy Documentation (flex-1) ───────────────── */}
        <div
          className={`flex-1 min-w-0 w-full ${
            mobilePane === "document" ? "block" : "hidden lg:block"
          }`}
        >
          <div className="solid-card overflow-hidden">
            {/* Card Header */}
            <div className="flex items-center justify-between gap-4 px-5 py-3.5 border-b border-border bg-muted/20">
              <h2 className="text-sm font-semibold text-foreground">Strategy Rules</h2>

              {isEditMode && (
                <div className="flex items-center bg-secondary p-0.5 rounded-lg border border-border">
                  <button
                    type="button"
                    onClick={() => setEditorTab("write")}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      editorTab === "write"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Write
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditorTab("preview")}
                    className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      editorTab === "preview"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Preview
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditorTab("split")}
                    className={`hidden lg:inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      editorTab === "split"
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
              {!isEditMode || editorTab === "preview" ? (
                renderMarkdownPreview()
              ) : editorTab === "split" ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                  <textarea
                    ref={textareaRef}
                    value={contentMarkdown}
                    onChange={(e) => setContentMarkdown(e.target.value)}
                    placeholder="Write your detailed strategy rules here using Markdown…"
                    aria-label="Playbook content (Markdown)"
                    className="w-full min-h-[480px] resize-y rounded-lg border border-border bg-background p-4 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                    spellCheck={false}
                  />
                  <div className="rounded-lg border border-border bg-muted/10 p-4 min-h-[480px]">
                    {renderMarkdownPreview()}
                  </div>
                </div>
              ) : (
                <textarea
                  ref={textareaRef}
                  value={contentMarkdown}
                  onChange={(e) => setContentMarkdown(e.target.value)}
                  placeholder="Write your detailed strategy rules here using Markdown…"
                  aria-label="Playbook content (Markdown)"
                  className="w-full min-h-[480px] resize-y rounded-lg border border-border bg-background p-4 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                  spellCheck={false}
                />
              )}
            </div>
          </div>
        </div>

        {/* ── Right Side Pane (Tags, Images, External Links) ────────────────── */}
        <aside
          className={`w-full lg:w-[360px] xl:w-[420px] shrink-0 flex-col gap-4 ${
            mobilePane === "details" ? "flex" : "hidden lg:flex"
          }`}
        >
          {/* 1. Tags Card */}
          <section className="solid-card p-4">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center justify-between">
              <span>Tags</span>
              {assignedTaxonomies.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {assignedTaxonomies.length}
                </span>
              )}
            </h3>

            <div className="flex flex-wrap gap-1.5 mb-2">
              {assignedTaxonomies.map((t) => (
                <span
                  key={t.id}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${contrastTextColor(
                    t.color_hex
                  )}`}
                  style={{ backgroundColor: t.color_hex }}
                >
                  {t.name}
                  {isEditMode && (
                    <button
                      type="button"
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

            {isEditMode && availableTaxonomies.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    assignTaxonomy({ playbookId: id, taxonomyId: e.target.value });
                    e.target.value = "";
                  }
                }}
                className="w-full mt-1 px-2.5 py-1.5 text-sm bg-secondary border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
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

          {/* 2. Images Card (16:9 Chart Thumbnails) */}
          <section className="solid-card p-4">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center justify-between">
              <span>Images</span>
              {visibleAttachments.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {visibleAttachments.length}
                </span>
              )}
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
                className={`flex flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed cursor-pointer transition-colors py-4 px-3 mb-3 text-center ${
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
                    <span className="text-xs text-muted-foreground">
                      PNG, JPG, GIF, WebP · max 20 MB
                    </span>
                  </>
                )}
              </div>
            )}
            {uploadError && <p className="mb-2 text-xs text-destructive">{uploadError}</p>}

            {/* Visual 16:9 Thumbnail Grid */}
            {visibleAttachments.length > 0 ? (
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {visibleAttachments.map((att) => {
                  const resolvedUrl = resolveStorageUrl(att.storage_url);
                  return (
                    <li
                      key={att.id}
                      className="group flex flex-col rounded-lg bg-secondary/60 border border-border overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setLightboxSrc(resolvedUrl);
                          setLightboxAlt(att.filename);
                        }}
                        className="relative aspect-video w-full bg-background overflow-hidden block"
                        aria-label={`View ${att.filename}`}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={resolvedUrl}
                          alt={att.filename}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                        />
                        {att.isPending && (
                          <span className="absolute top-1.5 left-1.5 text-[10px] px-1.5 py-0.5 rounded border border-primary/30 text-primary bg-background/90 font-medium">
                            Unsaved
                          </span>
                        )}
                      </button>

                      <div className="flex items-center gap-1.5 px-2.5 py-1.5 border-t border-border">
                        <span
                          className="flex-1 text-xs text-foreground truncate"
                          title={att.filename}
                        >
                          {att.filename}
                        </span>

                        {!att.isPending && (
                          <button
                            type="button"
                            onClick={() => handleInsertOrCopyImageRef(att.id, att.filename)}
                            className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors shrink-0"
                            title={
                              isEditMode
                                ? "Insert Markdown reference into document"
                                : "Copy Markdown reference"
                            }
                            aria-label={`Copy reference for ${att.filename}`}
                          >
                            {copiedAttachmentId === att.id ? (
                              <Check className="w-3.5 h-3.5 text-success" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}

                        {isEditMode && (
                          <button
                            type="button"
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
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              !isEditMode && <span className="text-xs text-muted-foreground italic">No images</span>
            )}
          </section>

          {/* 3. External Links Card */}
          <section className="solid-card p-4">
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center justify-between">
              <span>External Links</span>
              {links.length > 0 && (
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-[10px]">
                  {links.length}
                </span>
              )}
            </h3>

            {links.length > 0 ? (
              <ul className={isEditMode ? "space-y-1.5 mb-3" : "space-y-1.5"}>
                {links.map((link) => (
                  <li
                    key={link.id}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-secondary border border-border"
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
                        type="button"
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
            ) : (
              !isEditMode && <span className="text-xs text-muted-foreground italic">No links</span>
            )}

            {isEditMode && (
              <div className="space-y-2 p-2.5 bg-secondary/50 rounded-lg border border-border/60">
                <p className="text-[11px] font-medium text-muted-foreground">Add new link</p>
                <input
                  type="text"
                  value={linkLabel}
                  onChange={(e) => setLinkLabel(e.target.value.slice(0, 200))}
                  placeholder="Label (e.g. TradingView chart)"
                  className="w-full px-2.5 py-1.5 text-sm bg-background border border-border rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
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
                    className="flex-1 px-2.5 py-1.5 text-sm bg-background border border-border rounded-md text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <button
                    type="button"
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
        </aside>
      </div>

      {/* Lightbox */}
      {lightboxSrc && (
        <Lightbox src={lightboxSrc} alt={lightboxAlt} onClose={() => setLightboxSrc(null)} />
      )}
    </div>
  );
}
