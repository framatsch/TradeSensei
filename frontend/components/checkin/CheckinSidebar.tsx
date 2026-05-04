"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { CheckinMiniCalendar } from "./CheckinMiniCalendar";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Settings, FileText } from "lucide-react";

export function CheckinSidebar() {
  const { view, setView } = useCheckinParams();
  const pathname = usePathname();

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
          Navigation
        </h2>
        <div className="space-y-1">
          <Link
            href="/dashboard/settings/checkin"
            className={`flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              pathname.startsWith("/dashboard/settings/checkin")
                ? "text-primary bg-primary/10 font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>Definitions</span>
          </Link>
          <Link
            href="/dashboard/checkins"
            className={`flex items-center gap-3 px-3 py-2 text-sm transition-colors rounded-lg ${
              pathname === "/dashboard/checkins" || pathname === "/dashboard/checkin"
                ? "text-primary bg-primary/10 font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Timeline / Hub</span>
          </Link>
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-border">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          View Mode
        </h2>
        <div className="flex bg-secondary p-1 rounded-lg">
          <button
            onClick={() => setView("timeline")}
            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === "timeline" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Timeline
          </button>
          <button
            onClick={() => setView("modelbook")}
            className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${
              view === "modelbook" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Model Book
          </button>
        </div>
      </div>
    </div>
  );
}
