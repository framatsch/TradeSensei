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

import { useCheckinEntries } from "@/hooks/useCheckins";
import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Pencil, ExternalLink, Link2 } from "lucide-react";
import { TradeImageGallery } from "@/components/trades/TradeImageGallery";
import { CheckinLightbox } from "@/components/checkin/CheckinLightbox";

export function GalleryView() {
  const router = useRouter();
  const { filter, setFilter } = useCheckinFilter();
  const [lightboxData, setLightboxData] = useState<{ urls: string[]; index: number } | null>(null);

  const targetIndicesStr = filter.target_indices?.join(",") ?? undefined;
  const taxonomyIdsStr = filter.taxonomy_ids?.join(",") ?? undefined;
  const annotationFiltersStr =
    filter.annotation_filters && filter.annotation_filters.length > 0
      ? JSON.stringify(filter.annotation_filters.map(({ _key: _, ...rest }) => rest))
      : undefined;

  // Fetch more items for the gallery view
  const { data, isLoading, isError } = useCheckinEntries(
    filter.from_date ?? undefined,
    filter.to_date ?? undefined,
    targetIndicesStr,
    taxonomyIdsStr,
    annotationFiltersStr,
    filter.perPage * 2,
    (filter.page - 1) * (filter.perPage * 2)
  );

  if (isError) {
    return (
      <div className="p-12 text-center text-destructive border rounded-xl border-dashed bg-destructive/5">
        <p className="font-semibold">Failed to load check-ins</p>
        <p className="text-sm opacity-80 mt-1">Please check your filters or try again later.</p>
      </div>
    );
  }
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
          return (
            <div
              key={checkin.id}
              onClick={() => router.push(`/dashboard/checkins/${checkin.date}`)}
              className="group block relative bg-card border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all hover:border-[color-mix(in_srgb,var(--primary)_50%,transparent)] cursor-pointer"
            >
              {/* Image Thumbnail */}
              <div 
                className="aspect-video w-full bg-muted border-b border-border overflow-hidden relative p-4"
                onClick={(e) => {
                  if (checkin.screenshot_urls && checkin.screenshot_urls.length > 0) {
                    e.stopPropagation();
                    setLightboxData({ urls: checkin.screenshot_urls, index: 0 });
                  }
                }}
              >
                {checkin.screenshot_urls && checkin.screenshot_urls.length > 0 ? (
                  <div className="w-full h-full relative rounded-lg overflow-hidden shadow-sm">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img 
                      src={checkin.screenshot_urls[0]} 
                      alt={`Screenshot for ${checkin.date}`}
                      className="absolute inset-0 w-full h-full object-cover transition-transform group-hover:scale-105"
                    />
                  </div>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center text-[color-mix(in_srgb,var(--muted-foreground)_40%,transparent)] bg-background rounded-lg shadow-sm border border-[color-mix(in_srgb,var(--border)_50%,transparent)]">
                    <span className="text-sm font-medium">No Image</span>
                  </div>
                )}
                {checkin.screenshot_urls && checkin.screenshot_urls.length > 1 && (
                  <div className="absolute bottom-6 right-6 bg-[color-mix(in_srgb,var(--background)_80%,transparent)] backdrop-blur-sm text-foreground text-xs px-2 py-1 rounded-md font-medium border border-border shadow-sm">
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
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/dashboard/checkins/${checkin.date}?edit=true`);
                      }}
                      className="p-1 text-muted-foreground hover:text-primary hover:bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] rounded-md transition-colors"
                      title="Edit Check-in"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {checkin.target_indices && checkin.target_indices.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {checkin.target_indices.map((index) => {
                      if (index.tradingview_url) {
                        return (
                          <a
                            key={index.id}
                            href={index.tradingview_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-[#2962FF]/10 hover:bg-[#2962FF]/20 border border-[#2962FF]/20 rounded-md text-[10px] font-medium text-[#2962FF] dark:text-[#739aff] transition-colors"
                            title={`${index.name} Chart`}
                          >
                            <ExternalLink className="w-2.5 h-2.5" />
                            {index.symbol}
                          </a>
                        );
                      }
                      return (
                        <span
                          key={index.id}
                          className="px-1.5 py-0.5 rounded-md text-[10px] font-bold border bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] text-primary border-[color-mix(in_srgb,var(--primary)_20%,transparent)]"
                          title={index.name}
                        >
                          {index.symbol}
                        </span>
                      );
                    })}
                  </div>
                )}

                {/* News Links */}
                {checkin.news_links && checkin.news_links.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
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
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-[color-mix(in_srgb,var(--muted)_40%,transparent)] hover:bg-muted border border-border rounded-md text-[10px] font-medium text-foreground transition-colors"
                          >
                            <Link2 className="w-2.5 h-2.5 text-primary" />
                            <span className="truncate max-w-[100px]">{domain}</span>
                          </a>
                        );
                      } catch {
                        return null;
                      }
                    })}
                  </div>
                )}

                {checkin.notes ? (
                  <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                    {checkin.notes.replace(/[#*`_~\[\]()>-]/g, "")}
                  </p>
                ) : (
                  <p className="text-xs text-[color-mix(in_srgb,var(--muted-foreground)_50%,transparent)] italic">
                    No notes provided.
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
{/* Pagination placeholder */}
{data.total > filter.perPage && (
  <div className="flex items-center justify-between pt-4 border-t border-border">
     <div className="text-sm text-muted-foreground">
       Showing {data.items.length} of {data.total}
     </div>
     <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setFilter(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
          disabled={filter.page <= 1}
          className="px-3 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          onClick={() => setFilter(prev => ({ ...prev, page: prev.page + 1 }))}
          disabled={!data.next_cursor}
          className="px-3 py-1 text-sm border rounded hover:bg-muted disabled:opacity-50"
        >
          Next
        </button>
     </div>
  </div>
)}

      {lightboxData && (
        <CheckinLightbox
          urls={lightboxData.urls}
          initialIndex={lightboxData.index}
          onClose={() => setLightboxData(null)}
        />
      )}
    </div>
  );
}
