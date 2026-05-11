import { AnnotationDefinition } from "@/lib/api/types.gen";

interface Props {
  definitions: AnnotationDefinition[];
  values: Record<string, string | number | boolean>;
  onChange: (values: Record<string, string | number | boolean>) => void;
}

export function AnnotationInputs({ definitions, values, onChange }: Props) {
  if (!definitions || definitions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 border border-dashed border-border rounded-lg bg-secondary/30 h-full">
        <p className="text-sm text-muted-foreground text-center">No trade annotations found.</p>
      </div>
    );
  }

  const handleChange = (defId: string, value: string | number | boolean | null) => {
    const newValues = { ...values };
    if (value === null || value === "") {
      delete newValues[defId];
    } else {
      newValues[defId] = value;
    }
    onChange(newValues);
  };

  const inputCls = "w-full px-3 py-2 bg-secondary border border-border dark:border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary placeholder-zinc-500";
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
            
            {def.input_type === "bool" && (
              <label className="relative inline-flex items-center cursor-pointer mt-1">
                <input 
                  type="checkbox" 
                  className="sr-only peer" 
                  checked={val === true}
                  onChange={(e) => handleChange(def.id, e.target.checked)}
                />
                <div className="w-11 h-6 bg-secondary peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
              </label>
            )}
            
            {(def.input_type === "int" || def.input_type === "float") && (
              <input
                type="number"
                step={def.input_type === "int" ? "1" : "any"}
                min={def.min_value ?? undefined}
                max={def.max_value ?? undefined}
                className={inputCls}
                value={(val as number) ?? ""}
                onChange={(e) => {
                  const num = def.input_type === "int" ? parseInt(e.target.value) : parseFloat(e.target.value);
                  handleChange(def.id, isNaN(num) ? null : num);
                }}
              />
            )}
            
            {def.input_type === "string_enum" && def.options && (
              <select
                className={inputCls}
                value={(val as string) ?? ""}
                onChange={(e) => handleChange(def.id, e.target.value)}
              >
                <option value="">— Select —</option>
                {def.options.map((opt) => (
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
