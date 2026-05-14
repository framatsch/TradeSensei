import type { TaxonomyResponse } from "@/lib/types";
import { Check, Hash } from "lucide-react";

interface Props {
  taxonomies: TaxonomyResponse[];
  selectedIds: string[];
  onChange?: (selectedIds: string[]) => void;
  disabled?: boolean;
}

export function TaxonomySelector({ taxonomies, selectedIds, onChange, disabled }: Props) {
  if (!taxonomies || taxonomies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 border border-dashed border-border rounded-lg bg-secondary/30">
        <Hash className="w-8 h-8 text-muted-foreground/30 mb-2" />
        <p className="text-sm text-muted-foreground text-center">No trade taxonomies found.</p>
        {!disabled && (
          <p className="text-xs text-muted-foreground/60 text-center mt-1">Configure them in Settings.</p>
        )}
      </div>
    );
  }

  const toggle = (id: string) => {
    if (!onChange || disabled) return;
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((x) => x !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {taxonomies.map((tax) => {
        const isSelected = selectedIds.includes(tax.id);
        
        return (
          <button
            key={tax.id}
            type="button"
            disabled={disabled}
            onClick={() => toggle(tax.id)}
            className={`
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all
              border focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
              ${
                isSelected
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-secondary text-foreground border-border"
              }
              ${disabled ? 'opacity-70 cursor-default' : 'hover:border-primary/50 cursor-pointer'}
            `}
          >
            {isSelected && <Check className="w-3.5 h-3.5" />}
            {tax.name}
          </button>
        );
      })}
    </div>
  );
}
