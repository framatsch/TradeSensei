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

import React, { useState, useEffect, useMemo } from "react";
import { Edit2 } from "lucide-react";
import { MarkdownRenderer } from "../notes/MarkdownRenderer";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import {
  useAssignTradeTaxonomy,
  useRemoveTradeTaxonomy,
  useAssignTradeAnnotation,
  useUpdateTradeAnnotation,
  // useRemoveTradeAnnotation
} from "@/hooks/useTradeMetadata";
import { useUpdateTrade } from "@/hooks/useTrade";
import { useDeleteNote } from "@/hooks/useNotes";
import { usePlaybooks } from "@/hooks/usePlaybooks";
import type { AnnotationType, Trade } from "@/lib/types";
import { TaxonomySelector } from "./TaxonomySelector";
import { AnnotationInputs } from "./AnnotationInputs";

interface QualitativeMetadataPanelProps {
  trade: Trade;
  portfolioId?: string;
  onDirtyChange?: (dirty: boolean) => void;
}

/**
 * Normalizes a persisted annotation value for comparison/draft use: numeric-typed
 * annotations that come back as strings are coerced to numbers so they compare
 * equal to the numeric values held in draft state. Used both when pre-filling the
 * draft and when checking whether a value has changed, so the two never drift.
 */
function normalizeAnnotationValue(
  value: unknown,
  type: AnnotationType
): string | number | boolean | null | undefined {
  if (value === null || value === undefined) return value;
  if (typeof value === "string" && (type === "float" || type === "int")) {
    return Number(value);
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return value;
  return undefined;
}

/** Maps a trade's persisted annotation assignments into the draft-state shape keyed by definition id. */
function buildAnnotationDraft(trade: Trade): Record<string, string | number | boolean> {
  const draft: Record<string, string | number | boolean> = {};
  for (const annotation of trade.annotations ?? []) {
    const val = normalizeAnnotationValue(annotation.value, annotation.type);
    if (val === null || val === undefined) continue;
    draft[annotation.annotation_definition_id] = val;
  }
  return draft;
}

export function QualitativeMetadataPanel({ trade, portfolioId, onDirtyChange }: QualitativeMetadataPanelProps) {
  const [isSaving, setIsSaving] = useState(false);
  const quickNotesEnabled = useFeatureFlag("enable_quick_notes");

  const { data: taxonomies = [] } = useGetTaxonomies("trades");
  const { data: annotationDefs = [] } = useGetAnnotationDefinitions("trades");
  const { data: playbooks = [] } = usePlaybooks();

  const updateTrade = useUpdateTrade(trade.id);
  const deleteNote = useDeleteNote();
  const assignTaxonomy = useAssignTradeTaxonomy();
  const removeTaxonomy = useRemoveTradeTaxonomy();
  const assignAnnotation = useAssignTradeAnnotation();
  const updateAnnotation = useUpdateTradeAnnotation();

  // Draft state
  const [draftTradeId, setDraftTradeId] = useState(trade.id);
  const [draftJournal, setDraftJournal] = useState(trade.journal ?? "");
  const [journalTab, setJournalTab] = useState<"write" | "preview">("preview");
  // IDs of Quick Notes captured at import time — deleted on Save.
  const [importedNoteIds, setImportedNoteIds] = useState<string[]>([]);
  const [draftTaxonomyIds, setDraftTaxonomyIds] = useState<string[]>(
    trade.taxonomies?.map((t) => t.id) ?? []
  );
  const [draftAnnotations, setDraftAnnotations] = useState<Record<string, string | number | boolean>>(
    () => buildAnnotationDraft(trade)
  );
  const [draftPlaybookId, setDraftPlaybookId] = useState<string | null>(trade.playbook_id);

  // Reset only for a different trade; refetching this trade must preserve its draft.
  if (draftTradeId !== trade.id) {
    setDraftTradeId(trade.id);
    setDraftJournal(trade.journal ?? "");
    setJournalTab("preview");
    setDraftPlaybookId(trade.playbook_id);
    setDraftTaxonomyIds(trade.taxonomies?.map((t) => t.id) ?? []);
    setDraftAnnotations(buildAnnotationDraft(trade));
    setImportedNoteIds([]);
  }

  const selectablePlaybooks = useMemo(() => {
    return playbooks.filter((pb) => pb.is_active || pb.id === draftPlaybookId);
  }, [playbooks, draftPlaybookId]);
  


  const quickNotes = trade.trade_notes ?? [];

  const handleImportQuickNotes = () => {
    if (quickNotes.length === 0 || importedNoteIds.length > 0) return;
    setImportedNoteIds(quickNotes.map((n) => n.id));
    const bullets = quickNotes.map((n) => {
      const d = new Date(n.created_at);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const label = n.emotion ? `${hh}:${mm}, ${n.emotion}` : `${hh}:${mm}`;
      return `* **[${label}]** ${n.content}`;
    });
    setDraftJournal((prev) => {
      const existing = prev.trimEnd();
      return existing ? `${existing}\n\n${bullets.join("\n")}` : bullets.join("\n");
    });
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // 1. Playbook and Journal
      if (draftJournal !== (trade.journal ?? "") || draftPlaybookId !== trade.playbook_id) {
        await updateTrade.mutateAsync({ journal: draftJournal, playbook_id: draftPlaybookId });
      }

      // 1b. Delete the Quick Notes captured at import time (journal is persisted first).
      // Notes created after the import are preserved. On failure, importedNoteIds is
      // kept so the user can retry via Save.
      if (importedNoteIds.length > 0) {
        for (const noteId of importedNoteIds) {
          await deleteNote.mutateAsync({ tradeId: trade.id, noteId });
        }
        setImportedNoteIds([]);
      }

      // 2. Taxonomies
      const originalTaxIds = trade.taxonomies?.map((t) => t.id) ?? [];
      const addedTax = draftTaxonomyIds.filter((id) => !originalTaxIds.includes(id));
      const removedTax = originalTaxIds.filter((id) => !draftTaxonomyIds.includes(id));

      for (const id of addedTax) {
        await assignTaxonomy.mutateAsync({ tradeId: trade.id, taxonomyId: id, portfolioId });
      }
      for (const id of removedTax) {
        await removeTaxonomy.mutateAsync({ tradeId: trade.id, taxonomyId: id, portfolioId });
      }

      // 3. Annotations
      for (const def of annotationDefs) {
        const draftVal = draftAnnotations[def.id];
        const rawOriginal = trade.annotations?.find((a) => a.annotation_definition_id === def.id)?.value;
        const originalVal = normalizeAnnotationValue(rawOriginal, def.type);

        if (draftVal !== undefined && draftVal !== originalVal) {
          if (originalVal === undefined) {
            await assignAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal, portfolioId });
          } else {
            await updateAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal, portfolioId });
          }
        } else if (draftVal === undefined && originalVal !== undefined && originalVal !== null) {
          // Note: ideally we would remove it here using useRemoveTradeAnnotation
        }
      }

    } catch (e) {
      console.error("Failed to save qualitative metadata", e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setDraftJournal(trade.journal ?? "");
    setDraftPlaybookId(trade.playbook_id);
    setDraftTaxonomyIds(trade.taxonomies?.map((t) => t.id) ?? []);
    setDraftAnnotations(buildAnnotationDraft(trade));
    setImportedNoteIds([]);
  };

  const originalTaxIds = trade.taxonomies?.map((t) => t.id) ?? [];
  const taxChanged = JSON.stringify([...draftTaxonomyIds].sort()) !== JSON.stringify([...originalTaxIds].sort());
  const journalChanged = draftJournal !== (trade.journal ?? "");
  const playbookChanged = draftPlaybookId !== trade.playbook_id;
  const notesImported = importedNoteIds.length > 0;
  let annotationsChanged = false;
  for (const def of annotationDefs) {
    const draftVal = draftAnnotations[def.id];
    const rawOriginal = trade.annotations?.find((a) => a.annotation_definition_id === def.id)?.value;
    const originalVal = normalizeAnnotationValue(rawOriginal, def.type);
    if (draftVal !== undefined && draftVal !== originalVal) {
      annotationsChanged = true;
      break;
    }
  }

  const isDirty = draftTradeId === trade.id && (taxChanged || journalChanged || playbookChanged || notesImported || annotationsChanged);

  useEffect(() => {
    onDirtyChange?.(isDirty);
    return () => onDirtyChange?.(false);
  }, [isDirty, onDirtyChange]);

  const activeTaxonomies = taxonomies.filter(t => !t.is_archived || draftTaxonomyIds.includes(t.id));

  return (
    <div className="solid-card shadow-sm w-full">
      <div className="flex items-center justify-between p-5 border-b border-border">
        <h2 className="text-base font-semibold text-foreground">Qualitative Analysis &amp; Metadata</h2>
        {isDirty && (
          <div className="hidden lg:flex items-center gap-3">
            <span className="text-xs text-amber-500 font-medium">Unsaved changes</span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCancel}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm rounded hover:bg-secondary text-muted-foreground transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-3 py-1.5 text-sm rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {isSaving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="p-5 space-y-6">
        {/* Playbook */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">Playbook</label>
          <select
            value={draftPlaybookId || ""}
            onChange={(e) => setDraftPlaybookId(e.target.value === "" ? null : e.target.value)}
            disabled={isSaving}
            className="w-full rounded border border-border bg-secondary px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors appearance-none"
          >
            <option value="">{selectablePlaybooks.length ? "Select a playbook..." : "No playbooks"}</option>
            {selectablePlaybooks.map((pb) => (
              <option key={pb.id} value={pb.id}>
                {pb.name}{!pb.is_active ? " (Inactive)" : ""}
              </option>
            ))}
          </select>
        </div>

        {/* Taxonomies */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="block text-sm font-medium text-foreground">Tags (Taxonomies)</label>
          </div>
          <TaxonomySelector
            taxonomies={activeTaxonomies}
            selectedIds={draftTaxonomyIds}
            onChange={setDraftTaxonomyIds}
            disabled={isSaving}
          />
        </div>

        {/* Dynamic Annotations */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="block text-sm font-medium text-foreground">Annotations</label>
          </div>
          <AnnotationInputs
            definitions={annotationDefs}
            values={draftAnnotations}
            onChange={setDraftAnnotations}
            disabled={isSaving}
          />
        </div>

        {/* Journal */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm font-medium text-foreground">Journal</label>
            <div className="flex items-center gap-2">
              {quickNotesEnabled && quickNotes.length > 0 && journalTab === "write" && (
                <button
                  type="button"
                  onClick={handleImportQuickNotes}
                  disabled={importedNoteIds.length > 0 || isSaving}
                  title={importedNoteIds.length > 0 ? "Quick Notes imported — save to delete them" : "Append Quick Notes to the journal"}
                  className="px-2.5 py-1 text-xs font-medium rounded-md border border-border text-muted-foreground hover:text-foreground hover:border-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Import Quick Notes
                </button>
              )}
            </div>
          </div>
          {journalTab === "preview" ? (
            <div className="group relative bg-secondary border border-border rounded-xl p-4 min-h-[100px]">
              <div className="absolute top-3 right-3 flex gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 transition-opacity">
                <button
                  type="button"
                  onClick={() => setJournalTab("write")}
                  className="p-1 rounded-md text-muted-foreground hover:text-primary hover:bg-secondary transition-colors"
                  title="Edit journal"
                  aria-label="Edit journal"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              </div>
              <div className="pr-8">
                {draftJournal.trim() ? (
                  <MarkdownRenderer content={draftJournal} />
                ) : (
                  <span className="text-muted-foreground/50 italic text-sm">No journal entry. Click the edit icon to add one.</span>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-3 bg-secondary border border-primary rounded-xl p-4">
              <textarea
                value={draftJournal}
                disabled={isSaving}
                onChange={(e) => setDraftJournal(e.target.value)}
                placeholder="Write your post-trade summary and final reflection here. What went well? What went wrong? (Markdown supported)"
                className="w-full min-h-[150px] rounded-lg border border-border bg-background text-sm text-foreground px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary resize-y"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setJournalTab("preview")}
                  className="px-3 py-1.5 text-xs font-medium bg-primary hover:bg-primary/90 text-white rounded-md transition-colors"
                >
                  Done Editing
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {isDirty && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
          <div className="flex items-center justify-between gap-3 px-4 py-3">
            <span className="text-xs font-medium text-warning">Unsaved changes</span>
            <div className="flex items-center gap-2">
              <button type="button" onClick={handleCancel} disabled={isSaving} className="btn-ghost px-3 py-2 text-sm disabled:opacity-50">
                Cancel
              </button>
              <button type="button" onClick={handleSave} disabled={isSaving} className="btn-primary px-4 py-2 text-sm disabled:opacity-50">
                {isSaving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
