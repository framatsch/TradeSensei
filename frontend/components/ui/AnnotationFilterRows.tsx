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
import { PlusCircle, X } from "lucide-react";
import type { AnnotationDefinitionResponse } from "@/lib/api/types.gen";

export interface AnnotationFilterRow {
  annotation_definition_id: string;
  operator: string;
  value: string | number | boolean;
  logic: "and" | "or";
  _key?: string;
}

const OPERATORS_BY_TYPE: Record<string, { value: string; label: string }[]> = {
  bool: [{ value: "eq", label: "is" }],
  string_enum: [
    { value: "eq", label: "is" },
    { value: "neq", label: "is not" },
  ],
  int: [
    { value: "eq", label: "=" },
    { value: "neq", label: "≠" },
    { value: "lt", label: "<" },
    { value: "lte", label: "≤" },
    { value: "gt", label: ">" },
    { value: "gte", label: "≥" },
  ],
  float: [
    { value: "eq", label: "=" },
    { value: "neq", label: "≠" },
    { value: "lt", label: "<" },
    { value: "lte", label: "≤" },
    { value: "gt", label: ">" },
    { value: "gte", label: "≥" },
  ],
};

function defaultOperatorForType(type: string): string {
  return OPERATORS_BY_TYPE[type]?.[0]?.value ?? "eq";
}

function defaultValueForType(
  type: string,
  def: AnnotationDefinitionResponse
): string | number | boolean {
  if (type === "bool") return true;
  if (type === "string_enum") {
    const options = (def.scale_labels as { options?: string[] })?.options ?? [];
    return options[0] ?? "";
  }
  return 0;
}

// Shared class for all selects/inputs inside a chip
const CHIP_INPUT =
  "bg-transparent border-0 text-xs text-foreground focus:outline-none focus:ring-0 cursor-pointer py-0 px-0 max-w-[120px]";

interface AnnotationValueInputProps {
  definition: AnnotationDefinitionResponse;
  value: string | number | boolean;
  onChange: (v: string | number | boolean) => void;
}

function AnnotationValueInput({ definition, value, onChange }: AnnotationValueInputProps) {
  if (definition.type === "bool") {
    return (
      <select
        aria-label={`${definition.name} value`}
        value={String(value)}
        onChange={(e) => onChange(e.target.value === "true")}
        className={CHIP_INPUT}
      >
        <option value="true">True</option>
        <option value="false">False</option>
      </select>
    );
  }

  if (definition.type === "string_enum") {
    const options =
      (definition.scale_labels as { options?: string[] })?.options ?? [];
    return (
      <select
        aria-label={`${definition.name} value`}
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
        className={CHIP_INPUT}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  // int or float
  const isFloat = definition.type === "float";
  return (
    <input
      type="number"
      step={isFloat ? "any" : "1"}
      value={String(value)}
      onChange={(e) => {
        const n = isFloat
          ? parseFloat(e.target.value)
          : parseInt(e.target.value, 10);
        onChange(isNaN(n) ? 0 : n);
      }}
      className={`${CHIP_INPUT} w-14 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
    />
  );
}

interface AnnotationFilterRowsProps {
  rows: AnnotationFilterRow[];
  definitions: AnnotationDefinitionResponse[];
  onChange: (rows: AnnotationFilterRow[]) => void;
}

export function AnnotationFilterRows({
  rows,
  definitions,
  onChange,
}: AnnotationFilterRowsProps) {
  const addRow = useCallback(() => {
    if (!definitions.length) return;
    const def = definitions[0];
    onChange([
      ...rows,
      {
        annotation_definition_id: def.id,
        operator: defaultOperatorForType(def.type),
        value: defaultValueForType(def.type, def),
        logic: "and",
        _key: crypto.randomUUID(),
      },
    ]);
  }, [definitions, rows, onChange]);

  const removeRow = useCallback(
    (idx: number) => {
      onChange(rows.filter((_, i) => i !== idx));
    },
    [rows, onChange]
  );

  const updateRow = useCallback(
    (idx: number, patch: Partial<AnnotationFilterRow>) => {
      const updated = rows.map((r, i) => {
        if (i !== idx) return r;
        const next = { ...r, ...patch };
        if (
          patch.annotation_definition_id !== undefined &&
          patch.annotation_definition_id !== r.annotation_definition_id
        ) {
          const def = definitions.find(
            (d) => d.id === patch.annotation_definition_id
          );
          if (def) {
            next.operator = defaultOperatorForType(def.type);
            next.value = defaultValueForType(def.type, def);
          }
        }
        return next;
      });
      onChange(updated);
    },
    [rows, definitions, onChange]
  );

  if (!definitions.length) return null;

  return (
    <div className="flex flex-wrap gap-1.5 items-center">
      {rows.map((row, idx) => {
        const def =
          definitions.find((d) => d.id === row.annotation_definition_id) ??
          definitions[0];
        const operators = OPERATORS_BY_TYPE[def.type] ?? OPERATORS_BY_TYPE.int;

        return (
          <div
            key={row._key ?? idx}
            className="inline-flex items-center gap-1 bg-secondary border border-border/70 rounded-full pl-2 pr-1 py-1 text-xs"
          >
            {/* Logic connector pill — only for rows after the first */}
            {idx > 0 && (
              <button
                type="button"
                onClick={() =>
                  updateRow(idx, {
                    logic: row.logic === "and" ? "or" : "and",
                  })
                }
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border transition-colors mr-0.5 ${
                  row.logic === "or"
                    ? "bg-[color-mix(in_srgb,var(--warning)_15%,transparent)] border-[color-mix(in_srgb,var(--warning)_40%,transparent)] text-warning"
                    : "bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] border-[color-mix(in_srgb,var(--primary)_30%,transparent)] text-primary"
                }`}
                title="Click to toggle AND / OR"
              >
                {row.logic.toUpperCase()}
              </button>
            )}

            {/* Definition selector */}
            <select
              aria-label="Annotation field"
              value={row.annotation_definition_id}
              onChange={(e) =>
                updateRow(idx, { annotation_definition_id: e.target.value })
              }
              className={`${CHIP_INPUT} font-medium`}
            >
              {definitions.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>

            {/* Divider */}
            <span className="text-border select-none">·</span>

            {/* Operator */}
            <select
              aria-label="Operator"
              value={row.operator}
              onChange={(e) => updateRow(idx, { operator: e.target.value })}
              className={`${CHIP_INPUT} text-muted-foreground w-14`}
            >
              {operators.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>

            {/* Divider */}
            <span className="text-border select-none">·</span>

            {/* Value */}
            <AnnotationValueInput
              definition={def}
              value={row.value}
              onChange={(v) => updateRow(idx, { value: v })}
            />

            {/* Remove */}
            <button
              type="button"
              onClick={() => removeRow(idx)}
              className="ml-0.5 p-0.5 text-muted-foreground/50 hover:text-destructive transition-colors rounded-full"
              aria-label="Remove filter"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        );
      })}

      {/* Add button — flows inline with the chips */}
      <button
        type="button"
        onClick={addRow}
        className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary transition-colors px-2 py-1 rounded-full border border-dashed border-border/60 hover:border-primary/40"
      >
        <PlusCircle className="w-3 h-3" />
        Add
      </button>
    </div>
  );
}
