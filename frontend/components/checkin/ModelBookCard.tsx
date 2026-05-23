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

import Link from "next/link";
import { format } from "date-fns";
import { useRouter } from "next/navigation";
import { Star, Image as ImageIcon, Pencil } from "lucide-react";
import type { ModelBookTradeVariant, ModelBookCheckinVariant } from "@/lib/api/types.gen";
import { StarButton } from "@/components/shared/StarButton";
import { useCheckinModelBook } from "@/hooks/useCheckinModelBook";
import { useTradeModelBook } from "@/hooks/useTradeModelBook";

export type ModelBookEntryResponse = 
  | ({ type: "trade" } & ModelBookTradeVariant) 
  | ({ type: "checkin" } & ModelBookCheckinVariant);

export function ModelBookCard({ entry, onImageClick }: { entry: ModelBookEntryResponse; onImageClick: (url: string) => void }) {
  const router = useRouter();
  const checkinMutation = useCheckinModelBook();
  const tradeMutation = useTradeModelBook();

  if (entry.type === "trade") {
    const isLong = entry.direction === "LONG";
    const imageUrl = entry.image_urls?.[0];

    return (
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden flex flex-col group relative">
        {/* Type Badge & Star */}
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          <span className="bg-background/80 backdrop-blur-sm border border-border text-xs font-semibold px-2 py-1 rounded-md text-foreground">
            TRADE
          </span>
          <div className="bg-background/80 backdrop-blur-sm rounded-md border border-border">
            <StarButton 
              isStarred={true}
              isLoading={tradeMutation.isPending}
              onClick={() => tradeMutation.mutate({ tradeId: entry.id, isModelbook: false })}
              className="h-7 w-7"
            />
          </div>
        </div>

        {/* Image Preview */}
        <div 
          className="aspect-video bg-muted border-b border-border relative overflow-hidden flex items-center justify-center cursor-pointer group-hover:opacity-90 transition-opacity"
          onClick={() => imageUrl && onImageClick(imageUrl)}
        >
          {imageUrl ? (
            <img src={imageUrl} alt={entry.symbol} className="w-full h-full object-cover" />
          ) : (
            <div className="flex flex-col items-center text-muted-foreground">
              <ImageIcon className="w-8 h-8 mb-2 opacity-50" />
              <span className="text-xs">No image</span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4 flex flex-col flex-1">
          <div className="flex justify-between items-start mb-2">
            <div>
              <Link href={`/dashboard/trades/${entry.id}`} className="text-lg font-bold hover:underline">
                {entry.symbol}
              </Link>
              <div className="text-xs text-muted-foreground">
                {format(new Date(entry.date), "MMM d, yyyy")}
              </div>
            </div>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                isLong
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-400"
                  : "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400"
              }`}
            >
              {entry.direction}
            </span>
          </div>

          {entry.result_r && (
            <div className="mt-2 text-sm">
              <span className="text-muted-foreground mr-1">Result:</span>
              <span className={`font-semibold ${parseFloat(entry.result_r) > 0 ? "text-emerald-500" : parseFloat(entry.result_r) < 0 ? "text-red-500" : "text-foreground"}`}>
                {parseFloat(entry.result_r) > 0 ? "+" : ""}{parseFloat(entry.result_r).toFixed(2)} R
              </span>
            </div>
          )}

          {entry.tags && entry.tags.length > 0 && (
            <div className="mt-auto pt-4 flex flex-wrap gap-1.5">
              {entry.tags.map((tag) => (
                <span key={tag} className="bg-secondary text-muted-foreground text-[10px] px-1.5 py-0.5 rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  } else {
    // Checkin
    const imageUrl = entry.screenshot_urls?.[0];

    return (
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden flex flex-col group relative">
        {/* Type Badge & Star */}
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          <span className="bg-background/80 backdrop-blur-sm border border-border text-xs font-semibold px-2 py-1 rounded-md text-foreground">
            CHECK-IN
          </span>
          <div className="bg-background/80 backdrop-blur-sm rounded-md border border-border">
            <StarButton 
              isStarred={true}
              isLoading={checkinMutation.isPending}
              onClick={() => checkinMutation.mutate({ date: entry.date, isModelbook: false })}
              className="h-7 w-7"
            />
          </div>
        </div>

        {/* Image Preview */}
        <div 
          className="aspect-video bg-muted border-b border-border relative overflow-hidden flex items-center justify-center cursor-pointer group-hover:opacity-90 transition-opacity"
          onClick={() => imageUrl && onImageClick(imageUrl)}
        >
          {imageUrl ? (
            <img src={imageUrl} alt="Checkin" className="w-full h-full object-cover" />
          ) : (
            <div className="flex flex-col items-center text-muted-foreground">
              <ImageIcon className="w-8 h-8 mb-2 opacity-50" />
              <span className="text-xs">No screenshot</span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4 flex flex-col flex-1">
          <div className="flex justify-between items-start mb-2">
            <Link href={`/dashboard/checkins/${entry.date}`} className="text-lg font-bold hover:underline">
              {format(new Date(`${entry.date}T12:00:00Z`), "MMM d, yyyy")}
            </Link>
            <button
              onClick={(e) => {
                e.preventDefault();
                router.push(`/dashboard/checkins/${entry.date}?edit=true`);
              }}
              className="p-1 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-md transition-colors"
              title="Edit Check-in"
            >
              <Pencil className="w-4 h-4" />
            </button>
          </div>

          {entry.market_phase && (
            <div className="mt-2">
              <span
                className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border"
                style={{
                  backgroundColor: entry.regime_color ? `${entry.regime_color}20` : "var(--muted)",
                  color: entry.regime_color || "var(--foreground)",
                  borderColor: entry.regime_color ? `${entry.regime_color}40` : "var(--border)",
                }}
              >
                {entry.market_phase}
              </span>
            </div>
          )}
        </div>
      </div>
    );
  }
}
