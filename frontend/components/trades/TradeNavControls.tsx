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

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import type { useTradeNavigation } from "@/hooks/useTradeNavigation";

type Navigation = ReturnType<typeof useTradeNavigation>;

interface Props {
  navigation: Navigation;
  variant?: "desktop" | "compact";
}

export function TradePositionIndicator({ navigation }: { navigation: Navigation }) {
  if (!navigation.available) return null;
  return (
    <span className="whitespace-nowrap text-xs font-mono text-foreground"
      title={`Position in your filtered trade list (${navigation.sourceLabel})`}>
      {navigation.position} / {navigation.total ?? "—"}
    </span>
  );
}

export function TradeNavControls({ navigation, variant = "desktop" }: Props) {
  if (!navigation.available) return null;
  const compact = variant === "compact";
  const buttonClass = "btn-ghost inline-flex min-h-10 items-center justify-center gap-1 rounded-md px-2 text-sm disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
  return (
    <div className="flex flex-wrap items-center justify-end gap-2" aria-label="Trade navigation">
      <button type="button" className={buttonClass} onClick={navigation.goPrev}
        aria-label="Previous trade" disabled={!navigation.canGoPrev || navigation.isLoadingNext}
        title={`Previous${navigation.prevSymbol ? `: ${navigation.prevSymbol}` : ""} (←)`}>
        <ChevronLeft size={16} aria-hidden="true" />
        {!compact && "Previous"}
      </button>
      {!compact && <TradePositionIndicator navigation={navigation} />}
      <button type="button" className={buttonClass} onClick={() => void navigation.goNext()}
        aria-label="Next trade" disabled={!navigation.canGoNext || navigation.isLoadingNext}
        title={`Next${navigation.nextSymbol ? `: ${navigation.nextSymbol}` : ""} (→)`}>
        {!compact && "Next"}
        {navigation.isLoadingNext
          ? <Loader2 size={16} className="animate-spin" aria-label="Loading next trades" />
          : <ChevronRight size={16} aria-hidden="true" />}
      </button>
      {navigation.navigationError && <p role="alert" className="w-full text-xs text-danger">{navigation.navigationError}</p>}
    </div>
  );
}
