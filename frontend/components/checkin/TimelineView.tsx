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
import { useCheckinEntries } from "@/hooks/useCheckins";
import { useCheckinFilter } from "@/components/checkin/CheckinFilterContext";
import ReactMarkdown from "react-markdown";
import { format } from "date-fns";
import Link from "next/link";
import { ExternalLink, Pencil, Link2, Tag } from "lucide-react";
import { CheckinLightbox } from "@/components/checkin/CheckinLightbox";
import { resolveStorageUrl } from "@/lib/storageUrl";


export function TimelineView() {
  const router = useRouter();
  const { filter, setFilter } = useCheckinFilter();
  const [lightboxData, setLightboxData] = useState<{ urls: string[]; index: number } | null>(null);

  const targetIndicesStr = filter.target_indices?.join(",") ?? undefined;
  const taxonomyIdsStr = filter.taxonomy_ids?.join(",") ?? undefined;
  const annotationFiltersStr =
    filter.annotation_filters && filter.annotation_filters.length > 0
      ? JSON.stringify(filter.annotation_filters.map(({ _key: _, ...rest }) => rest))
      : undefined;

  const { data, isLoading, isError } = useCheckinEntries(
    filter.from_date ?? undefined,
    filter.to_date ?? undefined,
    targetIndicesStr,
    taxonomyIdsStr,
    annotationFiltersStr,
    filter.perPage,
    (filter.page - 1) * filter.perPage
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
      {data.items.map((checkin) => {
        // Market regime is now shown via annotation_assignments; use a neutral accent for the border
        const colorHex = "#94a3b8";

        return (
          <div
            key={checkin.id}
            onClick={() => router.push(`/dashboard/checkins/${checkin.date}`)}
            className="group relative solid-card shadow-sm flex flex-col sm:flex-row cursor-pointer hover:border-[color-mix(in_srgb,var(--primary)_50%,transparent)] transition-colors overflow-hidden"
          >
            {/* Image Thumbnail on the left */}
            {checkin.screenshot_urls && checkin.screenshot_urls.length > 0 && (
              <div 
                className="w-full sm:w-1/3 lg:w-1/4 shrink-0 border-b sm:border-b-0 sm:border-r border-border relative p-4 flex items-center justify-center cursor-pointer min-h-[200px]"
                onClick={(e) => {
                  e.stopPropagation();
                  setLightboxData({ urls: checkin.screenshot_urls!.map(resolveStorageUrl), index: 0 });
                }}
              >
                <div className="w-full h-full relative rounded-lg overflow-hidden shadow-sm min-h-[160px] sm:min-h-full">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={resolveStorageUrl(checkin.screenshot_urls[0])}
                    alt={`Screenshot for ${checkin.date}`}
                    className="absolute inset-0 w-full h-full object-cover transition-transform group-hover:scale-105"
                  />
                  {checkin.screenshot_urls.length > 1 && (
                    <div className="absolute bottom-2 right-2 bg-[color-mix(in_srgb,var(--background)_80%,transparent)] backdrop-blur-sm text-foreground text-xs px-2 py-1 rounded-md font-medium border border-border shadow-sm">
                      +{checkin.screenshot_urls.length - 1}
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="p-6 flex-1 flex flex-col">
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
                {/* Taxonomy tag badges */}
                {checkin.taxonomies && checkin.taxonomies.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {checkin.taxonomies.map((ta) => (
                      <span
                        key={ta.id}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        {ta.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {checkin.notes && (
                <div className="text-sm text-muted-foreground line-clamp-3 mb-4">
                  {checkin.notes.replace(/[#*`_~\[\]()>-]/g, "")}
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
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] hover:bg-[color-mix(in_srgb,var(--primary)_20%,transparent)] border border-[color-mix(in_srgb,var(--primary)_20%,transparent)] rounded-md text-xs font-medium text-primary transition-colors shadow-sm"
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
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[color-mix(in_srgb,var(--muted)_40%,transparent)] hover:bg-muted border border-border rounded-md text-xs font-medium text-foreground transition-colors shadow-sm"
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
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[color-mix(in_srgb,var(--muted)_40%,transparent)] hover:bg-muted border border-border rounded-md text-xs font-medium text-foreground transition-colors shadow-sm"
                        >
                          <Link2 className="w-3.5 h-3.5 text-primary" />
                          <span className="truncate max-w-[200px]">Link</span>
                        </a>
                      );
                    }
                  })}
                </div>
              )}
            </div>
          </div>
        );
      })}
{/* Pagination placeholder */}
{data.total > filter.perPage && (
  <div className="flex items-center justify-between pt-4">
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
