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

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";
import Link from "next/link";
import { ExternalLink, Pencil, Link2 } from "lucide-react";
import { TradeImageGallery } from "@/components/trades/TradeImageGallery";

export function TimelineView() {
  const router = useRouter();
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
            onClick={() => router.push(`/dashboard/checkins/${checkin.date}`)}
            className="relative bg-card border rounded-xl p-6 shadow-sm flex flex-col cursor-pointer hover:border-primary/50 transition-colors"
            style={{ borderLeftWidth: "4px", borderLeftColor: colorHex }}
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-semibold">
                  {format(new Date(`${checkin.date}T12:00:00Z`), "MMMM d, yyyy")}
                </h2>
                {checkin.target_indices && checkin.target_indices.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 ml-2">
                    {checkin.target_indices.map((index) => (
                      <span
                        key={index.id}
                        className="px-2 py-0.5 rounded-md text-xs font-bold border bg-primary/10 text-primary border-primary/20 shadow-sm"
                        title={index.name}
                      >
                        {index.symbol}
                      </span>
                    ))}
                  </div>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/dashboard/checkins/${checkin.date}?edit=true`);
                  }}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition-colors"
                  title="Edit Check-in"
                >
                  <Pencil className="w-4 h-4" />
                </button>
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

            {/* TradingView Charts for Indices */}
            {checkin.target_indices && checkin.target_indices.some(idx => idx.tradingview_url) && (
              <div className="mb-4 flex flex-wrap gap-2">
                {checkin.target_indices.map((index) => (
                  index.tradingview_url ? (
                    <a
                      key={index.id}
                      href={index.tradingview_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#2962FF]/10 hover:bg-[#2962FF]/20 border border-[#2962FF]/20 rounded-md text-xs font-medium text-[#2962FF] dark:text-[#739aff] transition-colors shadow-sm"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      {index.symbol} Chart
                    </a>
                  ) : null
                ))}
              </div>
            )}

            {/* News / External Links */}
            {checkin.news_links && checkin.news_links.length > 0 && (
              <div className="mb-4 flex flex-wrap gap-2">
                {checkin.news_links.map((link, i) => {
                  try {
                    const domain = new URL(link).hostname.replace('www.', '');
                    return (
                      <a
                        key={i}
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted/40 hover:bg-muted border border-border rounded-md text-xs font-medium text-foreground transition-colors shadow-sm"
                      >
                        <Link2 className="w-3.5 h-3.5 text-primary" />
                        <span className="truncate max-w-[200px]">{domain}</span>
                      </a>
                    );
                  } catch {
                    return (
                      <a
                        key={i}
                      href={link}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-muted/40 hover:bg-muted border border-border rounded-md text-xs font-medium text-foreground transition-colors shadow-sm"
                      >
                        <Link2 className="w-3.5 h-3.5 text-primary" />
                        <span className="truncate max-w-[200px]">Link</span>
                      </a>
                    );
                  }
                })}
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
