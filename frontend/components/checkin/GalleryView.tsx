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

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { format } from "date-fns";
import Link from "next/link";
import { TradeImageGallery } from "@/components/trades/TradeImageGallery";

export function GalleryView() {
  const { regime, fromDate, toDate, page, perPage, setPage } = useCheckinParams();
  
  // Fetch more items for the gallery view
  const { data, isLoading } = useCheckinEntries(fromDate ?? undefined, toDate ?? undefined, regime ?? undefined, perPage * 2);
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {data.items.map((checkin) => {
          const phase = phases?.find((p) => p.name === checkin.market_phase);
          const colorHex = phase?.color_hex ?? "var(--border)";

          return (
            <Link
              key={checkin.id}
              href={`/dashboard/checkins/${checkin.date}`}
              className="group block relative bg-card border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all hover:border-primary/50"
              style={{ borderTopWidth: "4px", borderTopColor: colorHex }}
            >
              {/* Image Thumbnail */}
              <div className="aspect-video w-full bg-muted border-b border-border overflow-hidden relative">
                {checkin.screenshot_urls && checkin.screenshot_urls.length > 0 ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img 
                    src={checkin.screenshot_urls[0]} 
                    alt={`Screenshot for ${checkin.date}`}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground/40 bg-muted/30">
                    <span className="text-sm font-medium">No Image</span>
                  </div>
                )}
                {checkin.screenshot_urls && checkin.screenshot_urls.length > 1 && (
                  <div className="absolute bottom-2 right-2 bg-background/80 backdrop-blur-sm text-foreground text-xs px-1.5 py-0.5 rounded font-medium border border-border">
                    +{checkin.screenshot_urls.length - 1}
                  </div>
                )}
              </div>

              {/* Card Body */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-bold text-foreground">
                    {format(new Date(`${checkin.date}T12:00:00Z`), "MMM d, yyyy")}
                  </h2>
                  {phase && (
                    <div
                      className="px-2 py-0.5 rounded-full text-[10px] font-medium border"
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

                {checkin.target_indices && checkin.target_indices.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {checkin.target_indices.map((index) => (
                      <span
                        key={index.id}
                        className="px-1.5 py-0.5 rounded-full text-[10px] font-medium border bg-muted/40 text-muted-foreground border-border"
                        title={index.name}
                      >
                        {index.symbol}
                      </span>
                    ))}
                  </div>
                )}

                {checkin.notes ? (
                  <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                    {checkin.notes.replace(/[#*`_~\[\]()>-]/g, "")}
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground/50 italic">
                    No notes provided.
                  </p>
                )}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination placeholder */}
      {data.total > (perPage * 2) && (
        <div className="flex items-center justify-between pt-4 border-t border-border">
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
