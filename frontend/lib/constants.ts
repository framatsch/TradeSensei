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
