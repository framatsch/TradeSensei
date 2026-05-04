"use client";

import { useState } from "react";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useMarketPhases } from "@/hooks/useCheckinDefinitions";
import { format } from "date-fns";
import { CheckinLightbox } from "./CheckinLightbox";
import { ModelBookFilterBar } from "./ModelBookFilterBar";

export function ModelBookView() {
  const { regime, fromDate, setFromDate, toDate, setToDate, page, perPage, setPage, setPerPage } = useCheckinParams();
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  
  const { data, isLoading } = useCheckinEntries(fromDate ?? undefined, toDate ?? undefined, regime ?? undefined, perPage);
  const { data: phases } = useMarketPhases();

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading model book...</div>;
  }

  return (
    <div className="space-y-6">
      <ModelBookFilterBar
        fromDate={fromDate}
        setFromDate={setFromDate}
        toDate={toDate}
        setToDate={setToDate}
        perPage={perPage}
        setPerPage={setPerPage}
      />

      {(!data?.items || data.items.length === 0) ? (
        <div className="p-12 text-center text-muted-foreground border rounded-xl border-dashed">
          No screenshots found for the current filters.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
            {data.items.map((checkin) => {
              // Only show checkins that have screenshots in Model Book view
              if (!checkin.screenshot_urls || checkin.screenshot_urls.length === 0) return null;

              const phase = phases?.find((p) => p.name === checkin.market_phase);
              const colorHex = phase?.color_hex ?? "#94a3b8";

              return checkin.screenshot_urls.map((url, i) => (
                 <div
                   key={`${checkin.id}-${i}`}
                   className="relative bg-card border rounded-xl overflow-hidden shadow-sm flex flex-col group cursor-pointer"
                   style={{ borderTopWidth: "4px", borderTopColor: colorHex }}
                   onClick={() => setLightboxUrl(url)}
                 >
                   <img
                     loading="lazy"
                     src={url}
                     alt={`Model Book Screenshot ${format(new Date(`${checkin.date}T12:00:00Z`), "MM/dd")}`}
                     className="w-full h-48 object-cover group-hover:opacity-90 transition-opacity"
                   />
                   <div className="p-4 flex items-center justify-between border-t border-border bg-muted/20">
                     <span className="text-sm font-medium">
                       {format(new Date(`${checkin.date}T12:00:00Z`), "MMM d, yyyy")}
                     </span>
                     {phase && (
                        <span 
                          className="text-xs px-2 py-0.5 rounded-full border"
                          style={{
                            backgroundColor: `${colorHex}15`,
                            borderColor: `${colorHex}40`,
                            color: colorHex,
                          }}
                        >
                          {phase.label}
                        </span>
                     )}
                   </div>
                 </div>
              ));
            })}
          </div>

          {lightboxUrl && (
            <CheckinLightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />
          )}

          {/* Pagination placeholder */}
          {data.total > perPage && (
            <div className="flex items-center justify-between pt-4 border-t">
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
        </>
      )}
    </div>
  );
}
