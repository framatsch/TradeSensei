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

import type { AnnotationDefinitionResponse } from "@/lib/api/types.gen";

interface Props {
  definitions: AnnotationDefinitionResponse[];
  values: Record<string, string | number | boolean>;
  onChange?: (values: Record<string, string | number | boolean>) => void;
  disabled?: boolean;
}

export function AnnotationInputs({ definitions, values, onChange, disabled }: Props) {
  if (!definitions || definitions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 border border-dashed border-border rounded-lg bg-secondary/30 h-full">
        <p className="text-sm text-muted-foreground text-center">No trade annotations found.</p>
        {!disabled && (
          <p className="text-xs text-muted-foreground/60 text-center mt-1">Configure them in Settings.</p>
        )}
      </div>
    );
  }

  const handleChange = (defId: string, value: string | number | boolean | null) => {
    if (!onChange || disabled) return;
    const newValues = { ...values };
    if (value === null || value === "") {
      delete newValues[defId];
    } else {
      newValues[defId] = value;
    }
    onChange(newValues);
  };

  const inputCls = `w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-zinc-500 disabled:opacity-50 disabled:cursor-not-allowed ${disabled ? 'appearance-none' : ''}`;
  const labelCls = "block text-xs font-medium text-muted-foreground mb-1.5";

  return (
    <div className="space-y-4">
      {definitions.map((def) => {
        const val = values[def.id];
        
        return (
          <div key={def.id}>
            <label className={labelCls}>
              {def.name}
              {def.description && (
                <span className="ml-1.5 font-normal text-muted-foreground/70" title={def.description}>
                  ⓘ
                </span>
              )}
            </label>
            
            {def.type === "bool" && (
              <label className={`relative inline-flex items-center mt-1 ${disabled ? 'cursor-default opacity-70' : 'cursor-pointer'}`}>
                <input 
                  type="checkbox" 
                  className="sr-only peer" 
                  checked={val === true}
                  disabled={disabled}
                  onChange={(e) => handleChange(def.id, e.target.checked)}
                />
                <div className="w-11 h-6 bg-secondary peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            )}
            
            {(def.type === "int" || def.type === "float") && (
              <input
                type="number"
                disabled={disabled}
                step={def.type === "int" ? "1" : "0.01"}
                min={
                  typeof def.scale_labels?.min === "number"
                    ? def.scale_labels.min
                    : undefined
                }
                max={
                  typeof def.scale_labels?.max === "number"
                    ? def.scale_labels.max
                    : undefined
                }
                className={inputCls}
                value={(val as number) ?? ""}
                onChange={(e) => {
                  const num = def.type === "int" ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
                  handleChange(def.id, isNaN(num) ? null : num);
                }}
              />
            )}
            
            {def.type === "string_enum" && Array.isArray(def.scale_labels?.options) && (
              <select
                className={inputCls}
                disabled={disabled}
                value={(val as string) ?? ""}
                onChange={(e) => handleChange(def.id, e.target.value)}
              >
                <option value="">— Select —</option>
                {def.scale_labels.options
                  .filter((opt): opt is string => typeof opt === "string")
                  .map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            )}
          </div>
        );
      })}
    </div>
  );
}
