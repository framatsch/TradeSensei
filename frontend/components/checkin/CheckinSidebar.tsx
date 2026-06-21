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

import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import { CheckinMiniCalendar } from "./CheckinMiniCalendar";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings, List, Grid } from "lucide-react";
import { useSidebarStore } from "@/stores/sidebarStore";

export function CheckinSidebar() {
  const { filter, setFilter } = useCheckinFilter();
  const pathname = usePathname();
  const setMobileOpen = useSidebarStore((state) => state.setMobileOpen);

  const isCheckinsRoute = pathname === "/dashboard/checkins" || pathname.startsWith("/dashboard/checkins/");

  return (
    <div className="flex flex-col h-full p-4">
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Calendar
        </h2>
        <CheckinMiniCalendar />
      </div>

      <div className="mb-6">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Views
        </h2>
        <div className="space-y-1">
          <button
            onClick={() => {
              if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=timeline";
              else setFilter(prev => ({ ...prev, view: "timeline", page: 1 }));
              setMobileOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              isCheckinsRoute && (filter.view === "timeline" || !filter.view)
                ? "text-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-[color-mix(in_srgb,var(--muted)_60%,transparent)]"
            }`}
          >
            <List className="w-4 h-4" />
            <span>Timeline</span>
          </button>

          <button
            onClick={() => {
              if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=gallery";
              else setFilter(prev => ({ ...prev, view: "gallery", page: 1 }));
              setMobileOpen(false);
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              isCheckinsRoute && filter.view === "gallery"
                ? "text-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-[color-mix(in_srgb,var(--muted)_60%,transparent)]"
            }`}
          >
            <Grid className="w-4 h-4" />
            <span>Gallery</span>
          </button>
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-border">
        <Link
          href="/dashboard/settings?tab=checkin"
          className="flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg text-muted-foreground hover:text-foreground hover:bg-[color-mix(in_srgb,var(--muted)_60%,transparent)]"
        >
          <Settings className="w-4 h-4" />
          <span>Check-in Settings</span>
        </Link>
      </div>
    </div>
  );
}
