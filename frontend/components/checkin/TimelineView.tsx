"use client";

import { useState } from "react";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";
import Link from "next/link";
import { ExternalLink, Pencil } from "lucide-react";
import { TradeImageGallery } from "@/components/trades/TradeImageGallery";

export function TimelineView() {
  const { regime, fromDate, toDate, page, perPage, setPage } = useCheckinParams();
  
  const { data, isLoading } = useCheckinEntries(fromDate ?? undefined, toDate ?? undefined, regime ?? undefined, perPage);
  const { data: phases } = useGetTaxonomies("checkins");

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
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">
                  {format(new Date(`${checkin.date}T12:00:00Z`), "MMMM d, yyyy")}
                </h2>
                {checkin.target_indices && checkin.target_indices.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5">
                    {checkin.target_indices.map((index) => (
                      <span
                        key={index.id}
                        className="px-2 py-0.5 rounded-full text-[10px] font-medium border bg-muted/40 text-muted-foreground border-border"
                        title={index.name}
                      >
                        {index.symbol}
                      </span>
                    ))}
                  </div>
                )}
                <Link
                  href={`/dashboard/checkins/${checkin.date}`}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
                  title="Edit Check-in"
                >
                  <Pencil className="w-4 h-4" />
                </Link>
              </div>
              {phase && (
                <div
                  className="px-2.5 py-0.5 rounded-full text-xs font-medium border"
                  style={{
                    backgroundColor: `${colorHex}15`,
                    borderColor: `${colorHex}40`,
                    color: colorHex,
                  }}
                >
                    {phase.name}
                  </div>
                )}
            </div>

            {checkin.notes && (
              <div className="prose prose-sm dark:prose-invert max-w-none mb-4">
                <ReactMarkdown>{checkin.notes}</ReactMarkdown>
              </div>
            )}

            {checkin.target_indices && checkin.target_indices.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {checkin.target_indices.map((index) => (
                  index.tradingview_url ? (
                    <a
                      key={index.id}
                      href={index.tradingview_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <ExternalLink className="w-3 h-3" />
                      {index.symbol}
                    </a>
                  ) : null
                ))}
              </div>
            )}

            {checkin.screenshot_urls && checkin.screenshot_urls.length > 0 && (
              <div className="mt-4">
                <TradeImageGallery imageUrls={checkin.screenshot_urls} />
              </div>
            )}
          </div>
        );
      })}

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
