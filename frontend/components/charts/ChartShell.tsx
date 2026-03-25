/**
 * ChartShell — shared card wrapper for all Recharts-based chart components.
 *
 * Handles the repeated outer layout (card border, title, empty state) so
 * each individual chart only needs to render its Recharts tree.
 */

"use client";

import type { ReactNode } from "react";

interface Props {
  /** Card heading shown above the chart. */
  title: string;
  /** Message shown when `isEmpty` is true. */
  emptyMessage?: string;
  /** When true the empty-state placeholder is rendered instead of children. */
  isEmpty: boolean;
  /** The Recharts component tree. */
  children: ReactNode;
  /** Additional Tailwind classes applied to the outer card div. */
  className?: string;
}

export function ChartShell({
  title,
  emptyMessage = "No data available yet.",
  isEmpty,
  children,
  className = "",
}: Props) {
  return (
    <div
      className={`bg-card text-card-foreground rounded-xl p-5 border border-border ${className}`}
    >
      <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">
        {title}
      </h3>
      {isEmpty ? (
        <p className="text-muted-foreground text-sm text-center py-12">
          {emptyMessage}
        </p>
      ) : (
        children
      )}
    </div>
  );
}
