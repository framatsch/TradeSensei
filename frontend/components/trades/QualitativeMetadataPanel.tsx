"use client";

import React, { useState, useRef, useEffect } from "react";
import { ChevronDown, Edit2 } from "lucide-react";
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
import { AnnotationInput } from "./AnnotationInput";

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
  const [draftTaxonomyIds, setDraftTaxonomyIds] = useState<string[]>(
    trade.taxonomies?.map((t) => t.id) ?? []
  );
  const [draftAnnotations, setDraftAnnotations] = useState<Record<string, string | number | boolean | null>>({});
  const [draftPlaybookId, setDraftPlaybookId] = useState<string | null>(trade.playbook_id);
  
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Reset draft state when not editing
    if (!isEditing) {
      setDraftNotes(trade.notes ?? "");
      setDraftTaxonomyIds(trade.taxonomies?.map((t) => t.id) ?? []);
      setDraftPlaybookId(trade.playbook_id);
      
      const annMap: Record<string, string | number | boolean | null> = {};
      trade.annotations?.forEach((a) => {
        annMap[a.annotation_definition_id] = a.value;
      });
      setDraftAnnotations(annMap);
    }
  }, [isEditing, trade]);

  useEffect(() => {
    if (!dropdownOpen) return;
    function handleClick(e: MouseEvent) {
      if (!dropdownRef.current?.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [dropdownOpen]);

  const toggleTaxonomy = (id: string) => {
    setDraftTaxonomyIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

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
          if (draftVal === null) {
            // we could remove it, but for simplicity we will just let user keep it or handle if useRemoveTradeAnnotation is implemented
          } else if (originalVal === undefined) {
            await assignAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal as any, portfolioId });
          } else {
            await updateAnnotation.mutateAsync({ tradeId: trade.id, annotationDefinitionId: def.id, value: draftVal as any, portfolioId });
          }
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
            onClick={() => setIsEditing(true)}
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
        <div className="relative" ref={dropdownRef}>
          <label className="block text-sm font-medium text-foreground mb-1.5">Tags (Taxonomies)</label>
          {!isEditing ? (
            <div className="flex flex-wrap gap-2">
              {draftTaxonomyIds.length > 0 ? (
                draftTaxonomyIds.map((id) => {
                  const tag = taxonomies.find(t => t.id === id);
                  if (!tag) return null;
                  return (
                    <span
                      key={id}
                      className="inline-flex items-center px-2 py-1 rounded text-xs font-medium border"
                      style={{ backgroundColor: tag.color_hex ? `${tag.color_hex}20` : '#f3f4f6', color: tag.color_hex || '#374151', borderColor: tag.color_hex ? `${tag.color_hex}40` : '#e5e7eb' }}
                    >
                      {tag.name}
                    </span>
                  );
                })
              ) : (
                <span className="text-sm text-muted-foreground italic">No tags assigned</span>
              )}
            </div>
          ) : (
            <div className="relative">
              <button
                type="button"
                className="w-full flex items-center justify-between rounded border border-border bg-secondary px-3 py-1.5 text-sm text-left focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                onClick={() => setDropdownOpen(!dropdownOpen)}
              >
                <span className={draftTaxonomyIds.length === 0 ? "text-muted-foreground" : "text-foreground"}>
                  {draftTaxonomyIds.length > 0
                    ? `${draftTaxonomyIds.length} tag(s) selected`
                    : "Select tags..."}
                </span>
                <ChevronDown size={14} className="opacity-50" />
              </button>

              {dropdownOpen && (
                <div className="absolute left-0 top-full mt-1 z-10 w-full rounded-md border border-border bg-card shadow-lg max-h-60 overflow-y-auto">
                  {activeTaxonomies.length === 0 ? (
                    <div className="px-3 py-2 text-sm text-muted-foreground">No tags available</div>
                  ) : (
                    activeTaxonomies.map((tax) => {
                      const isSelected = draftTaxonomyIds.includes(tax.id);
                      return (
                        <button
                          key={tax.id}
                          type="button"
                          className="w-full flex items-center px-3 py-2 text-sm hover:bg-secondary transition-colors"
                          onClick={() => toggleTaxonomy(tax.id)}
                        >
                          <div className={`mr-2 flex h-4 w-4 items-center justify-center rounded border ${isSelected ? 'bg-primary border-primary' : 'border-border'}`}>
                            {isSelected && <svg className="w-3 h-3 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
                          </div>
                          <span
                            className="inline-block w-2 h-2 rounded-full mr-2 flex-shrink-0"
                            style={{ backgroundColor: tax.color_hex || "#475569" }}
                          />
                          <span className="text-foreground truncate">{tax.name}</span>
                        </button>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Annotations */}
        {annotationDefs.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {annotationDefs.map((def) => (
              <AnnotationInput
                key={def.id}
                definition={def}
                disabled={!isEditing}
                value={draftAnnotations[def.id] ?? null}
                onChange={(val) => setDraftAnnotations((prev) => ({ ...prev, [def.id]: val }))}
              />
            ))}
          </div>
        )}

        {/* Journal */}
        <div>
          <label className="block text-sm font-medium text-foreground mb-1.5">Journal</label>
          <textarea
            value={draftNotes}
            onChange={(e) => setDraftNotes(e.target.value)}
            disabled={!isEditing}
            placeholder={isEditing ? "Write your thoughts here..." : "No journal entry."}
            className="w-full min-h-[100px] rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-transparent resize-y"
          />
        </div>
      </div>
    </div>
  );
}
