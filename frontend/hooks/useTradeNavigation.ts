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

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import { useTrades } from "@/hooks/useTrades";
import type { CursorPage, Trade } from "@/lib/types";
import {
  readTradeListContext,
  writeTradeListContext,
  upsertPage,
  type TradeListContext,
} from "@/lib/tradeListContext";

export function useTradeNavigation(tradeId: string, { isDirty = false } = {}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { activePortfolioId } = useActivePortfolio();
  const [context, setContext] = useState<TradeListContext | null>(null);
  const [isLoadingNext, setIsLoadingNext] = useState(false);
  const [navigationError, setNavigationError] = useState<string | null>(null);
  const requestInFlight = useRef(false);
  const lifecycle = useRef(0);
  const latestDirty = useRef(isDirty);

  useEffect(() => {
    latestDirty.current = isDirty;
  }, [isDirty]);

  useEffect(() => {
    lifecycle.current += 1;
    requestInFlight.current = false;
    setIsLoadingNext(false);
    setContext(readTradeListContext());
    setNavigationError(null);
    return () => { lifecycle.current += 1; };
  }, [tradeId, activePortfolioId]);

  const portfolioContext = context?.portfolioId === activePortfolioId ? context : null;
  const ids = portfolioContext?.pages.flatMap((page) => page.ids) ?? [];
  const index = ids.indexOf(tradeId);
  const available = !!portfolioContext && index !== -1;
  const prevId = available ? ids[index - 1] ?? null : null;
  const nextId = available ? ids[index + 1] ?? null : null;
  const lastPage = portfolioContext?.pages.at(-1);
  const canGoNext = available && (!!nextId || !!lastPage?.nextCursor);
  const nextPage = useTrades({
    portfolioId: portfolioContext?.portfolioId,
    cursor: lastPage?.nextCursor ?? undefined,
    limit: portfolioContext?.limit,
    filters: portfolioContext?.filters,
    sort: portfolioContext?.sort,
    enabled: false,
  });

  const confirmDiscard = useCallback(() =>
    !isDirty || window.confirm("Discard unsaved changes to this trade?"), [isDirty]);

  const goPrev = useCallback(() => {
    if (!prevId || requestInFlight.current || !confirmDiscard()) return;
    router.replace(`/dashboard/trades/${prevId}`);
  }, [prevId, confirmDiscard, router]);

  const goNext = useCallback(async () => {
    if (!canGoNext || !portfolioContext || requestInFlight.current) return;
    if (nextId) {
      if (!confirmDiscard()) return;
      router.replace(`/dashboard/trades/${nextId}`);
      return;
    }
    requestInFlight.current = true;
    setIsLoadingNext(true);
    setNavigationError(null);
    const requestLifecycle = lifecycle.current;
    try {
      const result = await nextPage.refetch();
      if (lifecycle.current !== requestLifecycle) return;
      if (result.isError || !result.data) {
        setNavigationError("Could not load the next trades. Please try again.");
        return;
      }
      // Check immediately before leaving: the user may have edited while loading.
      if (latestDirty.current && !window.confirm("Discard unsaved changes to this trade?")) return;
      const updated = upsertPage(portfolioContext, portfolioContext.pages.length, {
        cursor: lastPage?.nextCursor ?? null,
        ids: result.data.items.map((trade) => trade.id),
        nextCursor: result.data.next_cursor,
      });
      updated.total = result.data.total ?? portfolioContext.total;
      writeTradeListContext(updated);
      setContext(updated);
      const firstId = result.data.items[0]?.id;
      if (firstId) router.replace(`/dashboard/trades/${firstId}`);
    } catch {
      if (lifecycle.current === requestLifecycle) {
        setNavigationError("Could not load the next trades. Please try again.");
      }
    } finally {
      if (lifecycle.current === requestLifecycle) {
        requestInFlight.current = false;
        setIsLoadingNext(false);
      }
    }
  }, [canGoNext, portfolioContext, confirmDiscard, nextId, nextPage, lastPage, router]);

  const cachedSymbol = (id: string | null): string | null => {
    if (!id || !portfolioContext) return null;
    for (const page of portfolioContext.pages) {
      const cached = queryClient.getQueryData<CursorPage<Trade>>([
        "trades", portfolioContext.portfolioId, page.cursor ?? undefined,
        portfolioContext.limit, portfolioContext.filters, portfolioContext.sort,
      ]);
      const trade = cached?.items.find((item) => item.id === id);
      if (trade) return trade.symbol;
    }
    return null;
  };

  const hasFilters = portfolioContext && Object.values(portfolioContext.filters)
    .some((value) => Array.isArray(value) ? value.length > 0 : value !== undefined && value !== null && value !== "");
  const sourceLabel = portfolioContext?.viewName
    ? `View: ${portfolioContext.viewName}`
    : hasFilters ? "Filtered trade list" : "All trades";
  const listQuery = portfolioContext?.listQuery.replace(/^\?/, "") ?? "";

  return {
    available,
    prevId,
    nextId,
    canGoPrev: !!prevId,
    canGoNext,
    prevSymbol: cachedSymbol(prevId),
    nextSymbol: cachedSymbol(nextId),
    position: available ? index + 1 : null,
    total: portfolioContext?.total ?? null,
    sourceLabel,
    isLoadingNext,
    navigationError,
    goPrev,
    goNext,
    backHref: `/dashboard/trades${listQuery ? `?${listQuery}` : ""}`,
  };
}
