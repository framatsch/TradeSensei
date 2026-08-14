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

  const SECTION_HEADER_CLASS = "px-4 pt-4 pb-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-slate-500 select-none";
  const NAV_ITEM_CLASS = "w-full flex items-center gap-3 px-4 py-2 text-sm font-normal text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all duration-150 text-left";
  const NAV_ITEM_ACTIVE = "w-full flex items-center gap-3 px-4 py-2 text-sm font-medium nav-active transition-all duration-150 text-left";

  return (
    <div className="w-full h-full flex flex-col bg-sidebar overflow-y-auto pb-6">
      <div className={SECTION_HEADER_CLASS}>Calendar</div>
      <div className="px-4 pb-2">
        <CheckinMiniCalendar />
      </div>

      <div className={SECTION_HEADER_CLASS}>Views</div>
      <div className="space-y-0.5">
        <button
          onClick={() => {
            if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=timeline";
            else setFilter(prev => ({ ...prev, view: "timeline", page: 1 }));
            setMobileOpen(false);
          }}
          className={isCheckinsRoute && (filter.view === "timeline" || !filter.view) ? NAV_ITEM_ACTIVE : NAV_ITEM_CLASS}
        >
          <List className="w-4 h-4 shrink-0 opacity-70" />
          <span>Timeline</span>
        </button>

        <button
          onClick={() => {
            if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=gallery";
            else setFilter(prev => ({ ...prev, view: "gallery", page: 1 }));
            setMobileOpen(false);
          }}
          className={isCheckinsRoute && filter.view === "gallery" ? NAV_ITEM_ACTIVE : NAV_ITEM_CLASS}
        >
          <Grid className="w-4 h-4 shrink-0 opacity-70" />
          <span>Gallery</span>
        </button>
      </div>

      <div className="mt-auto pt-4 border-t border-border">
        <div className={SECTION_HEADER_CLASS}>Preferences</div>
        <Link
          href="/dashboard/settings?tab=checkin"
          className={NAV_ITEM_CLASS}
        >
          <Settings className="w-4 h-4 shrink-0 opacity-70" />
          <span>Check-in Settings</span>
        </Link>
      </div>
    </div>
  );
}
