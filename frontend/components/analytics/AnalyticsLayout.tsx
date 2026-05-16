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

"use client";

/**
 * AnalyticsLayout — L-shaped container for the Analytics Hub.
 *
 * Structure:
 *  ┌─ compact header (title + headerSlot) ────────────────────────────────┐
 *  ├─ optional banner ────────────────────────────────────────────────────┤
 *  ├─ left rail (196px) ──┬─ content pane (flex-1) ──────────────────────┤
 *  │  nav items           │  children                                    │
 *  └──────────────────────┴──────────────────────────────────────────────┘
 *
 * Active nav item: full-width solid background highlight so it reads as a
 * clear selected state, not just a thin indicator line.
 *
 * The left rail has a subtle background and is separated from the content
 * pane by a border-r so the two columns read as distinct regions without
 * requiring a wrapping card.
 */

import React from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AnalyticsTabConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
  description?: string;
}

interface AnalyticsLayoutProps {
  title: string;
  subtitle?: string;
  tabs: AnalyticsTabConfig[];
  activeTab: string;
  onTabChange: (tab: string) => void;
  /** Rendered at the right edge of the compact header (e.g. AccountFilter). */
  headerSlot?: React.ReactNode;
  /** Optional banner rendered between header and body (e.g. error message). */
  bannerSlot?: React.ReactNode;
  children: React.ReactNode;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AnalyticsLayout({
  title,
  subtitle,
  tabs,
  activeTab,
  onTabChange,
  headerSlot,
  bannerSlot,
  children,
}: AnalyticsLayoutProps) {
  return (
    <div className="flex flex-col">
      {/* ── Compact header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="min-w-0">
          <h1 className="text-base font-semibold text-foreground leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-lg">
              {subtitle}
            </p>
          )}
        </div>
        {headerSlot && (
          <div className="flex items-center gap-2 shrink-0 ml-4">
            {headerSlot}
          </div>
        )}
      </div>

      {/* Optional banner (error, warning, …) */}
      {bannerSlot && <div className="pt-2">{bannerSlot}</div>}

      {/* ── L-shape body ───────────────────────────────────────────────────── */}
      <div className="flex min-h-[560px] pt-4">
        {/* Left vertical navigation rail — fixed width, full-height bg */}
        <nav
          className="flex flex-col w-[196px] shrink-0 border-r border-border bg-muted/20 -ml-1 pl-1 pr-3 pt-1"
          aria-label="Analytics sections"
        >
          {tabs.map((tab) => {
            const isActive = tab.id === activeTab;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                role="tab"
                aria-selected={isActive}
                title={tab.description}
                className={[
                  "flex items-center gap-2.5 w-full px-3 py-2.5 text-sm font-medium rounded-md transition-all text-left",
                  isActive
                    ? "bg-primary/20 text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50",
                ].join(" ")}
              >
                <span
                  className={isActive ? "text-primary" : "text-muted-foreground"}
                >
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Right content pane */}
        <div className="flex-1 min-w-0 pl-5 pt-1">{children}</div>
      </div>
    </div>
  );
}
