/**
 * Loading skeleton components for Reporting Hub widgets.
 *
 * Mirrors the layout of real widgets to prevent cumulative layout shift (CLS)
 * while analytical queries are in flight.
 */

"use client";

function Pulse({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div
      className={`animate-pulse rounded bg-muted ${className ?? ""}`}
      style={style}
    />
  );
}

function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={`bg-card rounded-xl border border-border p-5 ${className ?? ""}`}>
      <Pulse className="h-3 w-20 mb-4" />
      <Pulse className="h-8 w-24 mb-2" />
      <Pulse className="h-3 w-16" />
    </div>
  );
}

/** Skeleton for the 5-card metrics row. */
export function MetricsSkeleton() {
  return (
    <div
      className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4"
      role="status"
      aria-label="Loading metrics"
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

/** Skeleton for a single chart panel (Performance Classic / Scatterplot / Attribution). */
export function ChartSkeleton({ height }: { height?: number }) {
  return (
    <div
      className="bg-card rounded-xl border border-border p-5 flex flex-col"
      role="status"
      aria-label="Loading chart"
    >
      <Pulse className="h-3 w-24 mb-4" />
      <Pulse
        className="flex-1 w-full rounded-md"
        style={{ height: `${height ?? 300}px` }}
      />
    </div>
  );
}

/** Two-column chart row skeleton. */
export function ChartRowSkeleton({ height }: { height?: number }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChartSkeleton height={height} />
      <ChartSkeleton height={height} />
    </div>
  );
}

/** Full widget-grid skeleton matching the real layout. */
export function WidgetGridSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      <MetricsSkeleton />
      <ChartRowSkeleton />
      <ChartRowSkeleton />
    </div>
  );
}
