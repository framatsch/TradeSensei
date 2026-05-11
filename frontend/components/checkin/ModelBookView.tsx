"use client";

import { useState } from "react";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { format } from "date-fns";
import { CheckinLightbox } from "./CheckinLightbox";
import { ModelBookFilterBar } from "./ModelBookFilterBar";
import { Image as ImageIcon } from "lucide-react";

export function ModelBookView() {
  const { regime, fromDate, setFromDate, toDate, setToDate, page, perPage, setPage, setPerPage } = useCheckinParams();
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  
  const { data, isLoading } = useCheckinEntries(fromDate ?? undefined, toDate ?? undefined, regime ?? undefined, perPage);
  const { data: phases } = useGetTaxonomies("checkins");

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading model book...</div>;
  }

  // Extract all screenshots from the fetched check-ins
  const screenshots = data?.items?.flatMap(checkin => 
    (checkin.screenshot_urls || []).map(url => ({
      url,
      checkin
    }))
  ) || [];

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

      {screenshots.length === 0 ? (
        <div className="p-12 flex flex-col items-center justify-center text-center border rounded-xl border-dashed bg-muted/10">
          <div className="w-12 h-12 mb-4 rounded-full bg-muted flex items-center justify-center">
            <ImageIcon className="w-6 h-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium text-foreground mb-1">Your Model Book is empty</h3>
          <p className="text-sm text-muted-foreground max-w-md">
            The Model Book is a visual gallery of your trades and setups. Add screenshots to your daily check-ins to build a library of chart patterns and market conditions.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
            {screenshots.map((item, i) => {
              const checkin = item.checkin;
              const phase = phases?.find((p) => p.name === checkin.market_phase);
              const colorHex = phase?.color_hex ?? "var(--border)";

              return (
                 <div
                   key={`${checkin.id}-${i}`}
                   className="relative bg-card border rounded-xl overflow-hidden shadow-sm flex flex-col group cursor-pointer hover:border-primary/50 transition-colors"
                   style={{ borderTopWidth: "4px", borderTopColor: colorHex }}
                   onClick={() => setLightboxUrl(item.url)}
                 >
                   {/* eslint-disable-next-line @next/next/no-img-element */}
                   <img
                     loading="lazy"
                     src={item.url}
                     alt={`Model Book Screenshot ${format(new Date(`${checkin.date}T12:00:00Z`), "MM/dd")}`}
                     className="w-full h-48 object-cover group-hover:opacity-90 transition-opacity"
                   />
                    <div className="p-4 flex items-center justify-between border-t border-border bg-muted/20">
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium">
                          {format(new Date(`${checkin.date}T12:00:00Z`), "MMM d, yyyy")}
                        </span>
                        {checkin.target_indices && checkin.target_indices.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {checkin.target_indices.map((index) => (
                              <span
                                key={index.id}
                                className="text-[10px] px-1.5 py-0.5 rounded-full border bg-muted/40 text-muted-foreground border-border"
                                title={index.name}
                              >
                                {index.symbol}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      {phase && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full border"
                          style={{
                            backgroundColor: `${colorHex}15`,
                            borderColor: `${colorHex}40`,
                            color: colorHex,
                          }}
                        >
                          {phase.name}
                        </span>
                      )}
                    </div>
                 </div>
              );
            })}
          </div>

          {lightboxUrl && (
            <CheckinLightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />
          )}

          {/* Pagination placeholder */}
          {data && data.total > perPage && (
            <div className="flex items-center justify-between pt-4 border-t border-border">
               <div className="text-sm text-muted-foreground">
                 Showing Check-ins page {page}
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
