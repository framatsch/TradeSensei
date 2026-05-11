import type { TaxonomyResponse } from "@/lib/types";

interface Props {
  taxonomy: Pick<TaxonomyResponse, "id" | "name" | "color_hex">;
}

export function TaxonomyBadge({ taxonomy }: Props) {
  const color = taxonomy.color_hex;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: color ? `${color}1a` : "var(--muted)",
        borderColor: color ? `${color}66` : "var(--border)",
        color: color ?? "var(--foreground)",
      }}
      title={taxonomy.name}
    >
      {taxonomy.name}
    </span>
  );
}
