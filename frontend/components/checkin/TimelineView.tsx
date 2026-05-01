"use client";

import { useState } from "react";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useMarketPhases } from "@/hooks/useCheckinDefinitions";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";
import { CheckinLightbox } from "./CheckinLightbox";

export function TimelineView() {
  const { regime, page, perPage, setPage } = useCheckinParams();
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  
  const { data, isLoading } = useCheckinEntries(undefined, undefined, regime ?? undefined, perPage);
  const { data: phases } = useMarketPhases();

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading check-ins...</div>;
  }

  if (!data?.items || data.items.length === 0) {
    return (
      <div className="p-12 text-center text-muted-foreground border rounded-xl border-dashed">
        No check-ins found for the current filters.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.items.map((checkin) => {
        const phase = phases?.find((p) => p.name === checkin.market_phase);
        const colorHex = phase?.color_hex ?? "#94a3b8";

        return (
          <div
            key={checkin.id}
            className="relative bg-card border rounded-xl p-6 shadow-sm flex flex-col"
            style={{ borderLeftWidth: "4px", borderLeftColor: colorHex }}
          >
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-lg font-semibold">
                {format(new Date(`${checkin.date}T12:00:00Z`), "MMMM d, yyyy")}
              </h2>
              {phase && (
                <div
                  className="px-2.5 py-0.5 rounded-full text-xs font-medium border"
                  style={{
                    backgroundColor: `${colorHex}15`,
                    borderColor: `${colorHex}40`,
                    color: colorHex,
                  }}
                >
                  {phase.label}
                </div>
              )}
            </div>

            {checkin.notes && (
              <div className="prose prose-sm dark:prose-invert max-w-none mb-4">
                <ReactMarkdown>{checkin.notes}</ReactMarkdown>
              </div>
            )}

            {checkin.screenshot_urls && checkin.screenshot_urls.length > 0 && (
              <div className="flex flex-wrap gap-3 mt-4">
                {checkin.screenshot_urls.map((url, i) => (
                  <button
                    key={i}
                    onClick={() => setLightboxUrl(url)}
                    className="overflow-hidden rounded-md border border-border bg-muted relative group"
                  >
                    <img
                      loading="lazy"
                      className="max-w-[120px] h-auto object-cover group-hover:opacity-90 transition-opacity"
                      src={url}
                      alt={`Screenshot ${i + 1}`}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}

      {lightboxUrl && (
        <CheckinLightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />
      )}

      {/* Pagination placeholder */}
      {data.total > perPage && (
        <div className="flex items-center justify-between pt-4">
           <div className="text-sm text-muted-foreground">
             Showing {data.items.length} of {data.total}
           </div>
           <div className="flex gap-2">
             <button 
                onClick={() => setPage(page - 1)} 
                disabled={page <= 1}
                className="px-3 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50"
              >
                Previous
              </button>
              <button 
                onClick={() => setPage(page + 1)} 
                disabled={!data.next_cursor}
                className="px-3 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50"
              >
                Next
              </button>
           </div>
        </div>
      )}
    </div>
  );
}
