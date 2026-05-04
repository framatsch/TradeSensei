"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { RegimePills } from "@/components/checkin/RegimePills";
import { TimelineView } from "@/components/checkin/TimelineView";
import { ModelBookView } from "@/components/checkin/ModelBookView";

interface Props {
  initialDate?: string;
}

export function CheckinsPageClient({ initialDate }: Props) {
  const { view } = useCheckinParams();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <h1 className="text-2xl font-bold mb-4">
          {initialDate ? `Check-in — ${initialDate}` : "Check-ins"}
        </h1>
        
        {/* Render RegimePills at the top of the main content area */}
        <RegimePills />

        {view === "timeline" ? (
          <TimelineView initialDate={initialDate} />
        ) : (
          <ModelBookView />
        )}
      </div>
    </div>
  );
}
