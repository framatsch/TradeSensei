/**
 * Shared constants for UI components.
 */

/**
 * Common colors used in Recharts components.
 * These should ideally match the CSS variables in globals.css.
 */
export const CHART_COLORS = {
  grid: "var(--border)",
  tick: "var(--muted-foreground)",
  axis: "var(--border)",
  tooltip: {
    bg: "var(--card)",
    border: "var(--border)",
    text: "var(--foreground)",
    label: "var(--muted-foreground)",
  },
  // Data colors
  primary: "#8b5cf6", // Violet 500 (Obsidian style)
  success: "#10b981", // emerald-500
  danger: "#f43f5e",  // rose-500
  warning: "#f59e0b", // amber-500
};
