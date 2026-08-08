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

import React, { useCallback } from "react";
import { X } from "lucide-react";
import type { AnnotationDefinitionResponse, CheckinAnnotationResponse } from "@/lib/api/types.gen";
import {
  useAssignCheckinAnnotation,
  useUpdateCheckinAnnotation,
  useRemoveCheckinAnnotation,
} from "@/hooks/useCheckinMetadata";

interface AnnotationEditorProps {
  /**
   * Checkin UUID, or null when the check-in hasn't been created yet.
   * When null, all changes are buffered in `pendingAnnotations`.
   */
  checkinId: string | null;
  definitions: AnnotationDefinitionResponse[];
  /** Current annotation assignments (from the loaded check-in's `annotations` field). */
  assigned: CheckinAnnotationResponse[];
  /**
   * Called when checkinId is null — buffer value changes for new check-ins.
   * Key is annotation_definition_id, value is the raw value (or null to clear).
   */
  onBufferChange?: (annotationDefinitionId: string, value: unknown) => void;
  /** Buffered values (for new check-ins, keyed by annotation_definition_id). */
  buffered?: Record<string, unknown>;
  isEditMode?: boolean;
}

function resolveValue(
  defId: string,
  assigned: CheckinAnnotationResponse[],
  buffered?: Record<string, unknown>
): unknown {
  if (buffered && defId in buffered) return buffered[defId];
  const a = assigned.find((x) => x.annotation_definition_id === defId);
  if (!a) return null;
  
  let val = a.value;
  if (typeof val === "string" && (a.type === "float" || a.type === "int")) {
    val = Number(val);
  }
  return val;
}

interface SingleAnnotationInputProps {
  definition: AnnotationDefinitionResponse;
  value: unknown;
  onChange: (v: unknown) => void;
  onClear: () => void;
  isEditMode: boolean;
}

function SingleAnnotationInput({ definition, value, onChange, onClear, isEditMode }: SingleAnnotationInputProps) {
  const inputClass =
    "bg-secondary text-foreground text-sm rounded border border-border px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary";

  const hasValue = value !== null && value !== undefined;

  if (definition.type === "bool") {
    return (
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={!isEditMode}
          onClick={() => onChange(!value)}
          className={`w-9 h-5 rounded-full transition-colors relative ${value ? "bg-primary" : "bg-muted-foreground/30"} disabled:cursor-default`}
          aria-label={`Toggle ${definition.name}`}
        >
          <span
            className={`absolute top-0.5 h-4 w-4 rounded-full bg-primary-foreground shadow transition-transform ${value ? "translate-x-4" : "translate-x-0.5"}`}
          />
        </button>
        <span className="text-sm text-muted-foreground">{value ? "Yes" : "No"}</span>
        {isEditMode && hasValue && (
          <button type="button" onClick={onClear} className="text-muted-foreground hover:text-destructive">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  if (definition.type === "string_enum") {
    const options = (definition.scale_labels as { options?: string[] })?.options ?? [];
    if (!isEditMode) {
      return <span className="text-sm text-foreground">{hasValue ? String(value) : <em className="text-muted-foreground">—</em>}</span>;
    }
    return (
      <div className="flex items-center gap-1.5">
        <select
          aria-label={definition.name}
          value={hasValue ? String(value) : ""}
          onChange={(e) => onChange(e.target.value || null)}
          className={inputClass}
          disabled={!isEditMode}
        >
          <option value="">—</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        {hasValue && (
          <button type="button" onClick={onClear} className="text-muted-foreground hover:text-destructive">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  // int or float
  const isFloat = definition.type === "float";
  const scaleMeta = definition.scale_labels as { min?: number; max?: number } | null;
  if (!isEditMode) {
    return <span className="text-sm text-foreground">{hasValue ? String(value) : <em className="text-muted-foreground">—</em>}</span>;
  }
  return (
    <div className="flex items-center gap-1.5">
      <input
        aria-label={definition.name}
        type="number"
        step={isFloat ? "any" : "1"}
        min={scaleMeta?.min}
        max={scaleMeta?.max}
        value={hasValue ? String(value) : ""}
        onChange={(e) => {
          const n = isFloat ? parseFloat(e.target.value) : parseInt(e.target.value, 10);
          onChange(isNaN(n) ? null : n);
        }}
        className={`${inputClass} w-24`}
        disabled={!isEditMode}
      />
      {scaleMeta?.min !== undefined && scaleMeta?.max !== undefined && (
        <span className="text-xs text-muted-foreground">
          {scaleMeta.min}–{scaleMeta.max}
        </span>
      )}
      {hasValue && (
        <button type="button" onClick={onClear} className="text-muted-foreground hover:text-destructive">
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

export function AnnotationEditor({
  checkinId,
  definitions,
  assigned,
  onBufferChange,
  buffered,
  isEditMode = true,
}: AnnotationEditorProps) {
  const assignMutation = useAssignCheckinAnnotation();
  const updateMutation = useUpdateCheckinAnnotation();
  const removeMutation = useRemoveCheckinAnnotation();

  const handleChange = useCallback(
    async (defId: string, newValue: unknown) => {
      if (!isEditMode) return;

      if (checkinId === null) {
        // Buffer for new check-in
        onBufferChange?.(defId, newValue);
        return;
      }

      const existing = assigned.find((a) => a.annotation_definition_id === defId);
      if (newValue === null || newValue === undefined) {
        if (existing) {
          await removeMutation.mutateAsync({ checkinId, annotationDefinitionId: defId });
        }
        return;
      }

      if (existing) {
        await updateMutation.mutateAsync({ checkinId, annotationDefinitionId: defId, value: newValue });
      } else {
        await assignMutation.mutateAsync({ checkinId, annotationDefinitionId: defId, value: newValue });
      }
    },
    [checkinId, assigned, isEditMode, onBufferChange, assignMutation, updateMutation, removeMutation]
  );

  const handleClear = useCallback(
    (defId: string) => handleChange(defId, null),
    [handleChange]
  );

  if (!definitions.length) return null;

  return (
    <div className="flex flex-col gap-3">
      {definitions.map((def) => {
        const currentValue = resolveValue(def.id, assigned, buffered);
        return (
          <div key={def.id} className="flex items-center justify-between gap-4">
            <span className="text-sm font-medium text-foreground shrink-0 w-36 truncate" title={def.name}>
              {def.name}
            </span>
            <SingleAnnotationInput
              definition={def}
              value={currentValue}
              onChange={(v) => void handleChange(def.id, v)}
              onClear={() => void handleClear(def.id)}
              isEditMode={isEditMode}
            />
          </div>
        );
      })}
    </div>
  );
}
