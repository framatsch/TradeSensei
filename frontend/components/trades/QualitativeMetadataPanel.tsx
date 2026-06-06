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

import React, { useState, useEffect, useRef } from "react";
import { Edit2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useSettings } from "@/hooks/useSettings";
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
import { usePlaybooks } from "@/hooks/usePlaybooks";
import type { Trade } from "@/lib/types";
import { TaxonomySelector } from "./TaxonomySelector";
import { AnnotationInputs } from "./AnnotationInputs";
import Link from "next/link";

interface QualitativeMetadataPanelProps {
  trade: Trade;
  portfolioId?: string;
}

export function QualitativeMetadataPanel({ trade, portfolioId }: QualitativeMetadataPanelProps) {
  const [isEditing, setIsEditing] = useState(false);

  const { data: taxonomies = [] } = useGetTaxonomies("trades");
  const { data: annotationDefs = [] } = useGetAnnotationDefinitions("trades");
  const { data: playbooks = [] } = usePlaybooks();

  const updateTrade = useUpdateTrade(trade.id);
  const assignTaxonomy = useAssignTradeTaxonomy();
  const removeTaxonomy = useRemoveTradeTaxonomy();
  const assignAnnotation = useAssignTradeAnnotation();
  const updateAnnotation = useUpdateTradeAnnotation();

  // Draft state
  const [draftNotes, setDraftNotes] = useState(trade.notes ?? "");
  const [notesTab, setNotesTab] = useState<"write" | "preview">("write");
  const lastTradeIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (
      draftNotes.trim().length > 0 &&
      trade.id === lastTradeIdRef.current
    ) {
      setNotesTab("preview");
    }
    lastTradeIdRef.current = trade.id;
  }, [trade.id, draftNotes]);

  const [draftTaxonomyIds, setDraftTaxonomyIds] = useState<string[]>(
    trade.taxonomies?.map((t) => t.id) ?? []
  );
  const [draftAnnotations, setDraftAnnotations] = useState<Record<string, string | number | boolean>>({});
  const [draftPlaybookId, setDraftPlaybookId] = useState<string | null>(trade.playbook_id);
  


  const handleSave = async () => {
    try {
      // 1. Playbook and Notes
      if (draftNotes !== (trade.notes ?? "") || draftPlaybookId !== trade.playbook_id) {
        await updateTrade.mutateAsync({ notes: draftNotes, playbook_id: draftPlaybookId });
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
        const originalVal = trade.annotations?.find((a) => a.annotation_definition_id === def.id)?.value;

        if (draftVal !== undefined && draftVal !== originalVal) {
          if (originalVal === undefined) {
            await assignAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal as any, portfolioId });
          } else {
            await updateAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal as any, portfolioId });
          }
        } else if (draftVal === undefined && originalVal !== undefined && originalVal !== null) {
          // Note: ideally we would remove it here using useRemoveTradeAnnotation
        }
      }

      setIsEditing(false);
    } catch (e) {
      console.error("Failed to save qualitative metadata", e);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const activeTaxonomies = taxonomies.filter(t => !t.is_archived || draftTaxonomyIds.includes(t.id));

  return (
    <div className="bg-card rounded-xl border border-border shadow-sm w-full">
      <div className="flex items-center justify-between p-5 border-b border-border">
        <h2 className="text-base font-semibold text-foreground">Qualitative Analysis &amp; Metadata</h2>
        {!isEditing ? (
          <button
            type="button"
            onClick={() => {
              setIsEditing(true);
              setNotesTab("write");
            }}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <Edit2 size={14} />
            Edit
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              className="px-3 py-1.5 text-sm rounded hover:bg-secondary text-muted-foreground transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1.5 text-sm rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Save
            </button>
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
            disabled={!isEditing}
            className="w-full rounded border border-border bg-secondary px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors appearance-none"
          >
            <option value="">{playbooks.length ? "Select a playbook..." : "No playbooks"}</option>
            {playbooks.map(pb => (
              <option key={pb.id} value={pb.id}>{pb.name}</option>
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
            disabled={!isEditing}
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
            disabled={!isEditing}
          />
        </div>

        {/* Journal */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-sm font-medium text-foreground">Journal</label>
            {isEditing && (
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
          {(!isEditing || notesTab === "preview") ? (
            <div className="w-full min-h-[100px] rounded-md border border-border bg-secondary/50 px-3 py-2 text-sm text-foreground prose prose-sm dark:prose-invert max-w-none">
              {draftNotes.trim() ? (
                <ReactMarkdown>{draftNotes}</ReactMarkdown>
              ) : (
                <span className="text-muted-foreground/50 italic">No journal entry.</span>
              )}
            </div>
          ) : (
            <textarea
              value={draftNotes}
              onChange={(e) => setDraftNotes(e.target.value)}
              placeholder="Write your thoughts here... (Markdown supported)"
              className="w-full min-h-[100px] rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          )}
        </div>
      </div>
    </div>
  );
}
