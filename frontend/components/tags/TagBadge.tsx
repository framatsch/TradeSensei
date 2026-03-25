/**
 * TagBadge — small colored chip for a single tag.
 * Used in trade rows and trade detail.
 */

import type { Tag } from "@/lib/types";

interface Props {
  tag: Tag;
  /** If provided, renders a dismiss button inside the badge. */
  onRemove?: () => void;
}

/** Derive a legible text color (black or white) from a hex background. */
function contrastTextColor(hex: string | null): string {
  if (!hex) return "text-foreground";
  const raw = hex.replace("#", "");
  const r = parseInt(raw.substring(0, 2), 16);
  const g = parseInt(raw.substring(2, 4), 16);
  const b = parseInt(raw.substring(4, 6), 16);
  // Perceived luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.55 ? "text-zinc-900" : "text-white";
}

export function TagBadge({ tag, onRemove }: Props) {
  const bgColor = tag.color ?? "#475569";
  const textClass = contrastTextColor(tag.color);

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${textClass}`}
      style={{ backgroundColor: bgColor }}
      title={tag.name}
    >
      {tag.name}
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          aria-label={`Remove tag ${tag.name}`}
          className="ml-0.5 hover:opacity-70 transition-opacity leading-none"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            className="w-3 h-3"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </span>
  );
}
