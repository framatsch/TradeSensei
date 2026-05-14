"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { CheckinMiniCalendar } from "./CheckinMiniCalendar";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings, List, Grid, BookOpen } from "lucide-react";

export function CheckinSidebar() {
  const { view, setView } = useCheckinParams();
  const pathname = usePathname();

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
              else setView("timeline");
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              isCheckinsRoute && (view === "timeline" || !view)
                ? "text-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <List className="w-4 h-4" />
            <span>Timeline</span>
          </button>

          <button
            onClick={() => {
              if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=gallery";
              else setView("gallery");
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              isCheckinsRoute && view === "gallery"
                ? "text-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <Grid className="w-4 h-4" />
            <span>Gallery</span>
          </button>

          <button
            onClick={() => {
              if (!isCheckinsRoute) window.location.href = "/dashboard/checkins?view=modelbook";
              else setView("modelbook");
            }}
            className={`w-full flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              isCheckinsRoute && view === "modelbook"
                ? "text-primary bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>Model Book</span>
          </button>
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-border">
        <Link
          href="/dashboard/settings?tab=checkin"
          className="flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60"
        >
          <Settings className="w-4 h-4" />
          <span>Check-in Settings</span>
        </Link>
      </div>
    </div>
  );
}
