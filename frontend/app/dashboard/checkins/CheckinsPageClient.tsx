"use client";

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { RegimePills } from "@/components/checkin/RegimePills";
import { TimelineView } from "@/components/checkin/TimelineView";
import { ModelBookView } from "@/components/checkin/ModelBookView";
import { GalleryView } from "@/components/checkin/GalleryView";
import Link from "next/link";
import { PlusCircle } from "lucide-react";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CheckinsPageClient() {
  const { view } = useCheckinParams();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">
            Check-ins
          </h1>
          <Link 
            href={`/dashboard/checkins/${today()}`}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            Today's Check-in
          </Link>
        </div>
        
        {/* Render RegimePills at the top of the main content area */}
        <RegimePills />

        {view === "gallery" ? (
          <GalleryView />
        ) : view === "modelbook" ? (
          <ModelBookView />
        ) : (
          <TimelineView />
        )}
      </div>
    </div>
  );
}
