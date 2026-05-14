"use client";

import { useState } from "react";
import { useCheckinParams } from "@/hooks/useCheckinParams";
import { useModelBookEntries } from "@/hooks/useModelBookEntries";
import { CheckinLightbox } from "./CheckinLightbox";
import { ModelBookFilterBar } from "./ModelBookFilterBar";
import { ModelBookCard } from "./ModelBookCard";
import { Star } from "lucide-react";
import Link from "next/link";

export function ModelBookView() {
  const { entityType, setEntityType, fromDate, setFromDate, toDate, setToDate, page, perPage, setPage, setPerPage } = useCheckinParams();
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  
  const { data, isLoading } = useModelBookEntries(entityType, fromDate ?? undefined, toDate ?? undefined, page, perPage);

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading model book...</div>;
  }

  const items = data?.items || [];
  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0;
  const hasPages = totalPages > 1;

  return (
    <div className="space-y-6">
      <ModelBookFilterBar
        entityType={entityType as any}
        setEntityType={setEntityType as any}
        fromDate={fromDate}
        setFromDate={setFromDate}
        toDate={toDate}
        setToDate={setToDate}
        perPage={perPage}
        setPerPage={setPerPage}
      />

      {items.length === 0 ? (
        <div className="bg-card border border-dashed border-border rounded-xl p-12 text-center flex flex-col items-center">
          <div className="bg-muted p-4 rounded-full mb-4">
            <Star className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-xl font-bold mb-2">Your Model Book is Empty</h3>
          <p className="text-muted-foreground max-w-md mx-auto mb-6">
            The Model Book is a gallery of your best setups and most insightful market check-ins. 
            Star items to add them here for review and pattern recognition.
          </p>
          <div className="flex gap-4">
            <Link href="/dashboard/trades" className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
              Browse Trades
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((entry) => (
            <ModelBookCard 
              key={`${entry.type}-${entry.id}`} 
              entry={entry} 
              onImageClick={setLightboxUrl} 
            />
          ))}
        </div>
      )}

      {hasPages && (
        <div className="flex justify-between items-center bg-card p-4 rounded-xl border border-border shadow-sm mt-6">
          <button
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
            className="px-4 py-2 bg-secondary text-foreground rounded hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
            className="px-4 py-2 bg-secondary text-foreground rounded hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            Next
          </button>
        </div>
      )}

      {lightboxUrl && (
        <CheckinLightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />
      )}
    </div>
  );
}
