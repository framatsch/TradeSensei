"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { CheckinMiniCalendar } from "./CheckinMiniCalendar";

export function CheckinSidebar() {
  const { view, setView } = useCheckinParams();

  return (
    <div className="flex flex-col h-full p-4 space-y-6">
      <div>
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

      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Calendar
        </h2>
        <CheckinMiniCalendar />
      </div>
    </div>
  );
}
