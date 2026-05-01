/**
 * Explicit empty-state component for the Reporting Hub.
 */

"use client";

import { BarChart3 } from "lucide-react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title?: string;
  description?: string;
}

export function EmptyState({
  icon,
  title = "No data to display",
  description = "No trades match the current filters.",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 text-muted-foreground/40">
        {icon ?? <BarChart3 className="w-12 h-12" />}
      </div>
      <h3 className="text-sm font-semibold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-xs">{description}</p>
    </div>
  );
}
