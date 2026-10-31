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

import { Fragment, useId, useState, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Edit2, RefreshCw, Save, Trash2, X } from "lucide-react";
import type { TradeFilters } from "@/hooks/useTrades";
import { countActiveFilters, FILTER_GROUPS, type FilterFieldKey, type FilterGroupKey } from "@/lib/tradeFilterFields";
import type { SavedTradeFilterRead } from "@/lib/types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  trigger?: ReactNode;
  filters: TradeFilters;
  renderField: (key: FilterFieldKey) => ReactNode;
  onClear: () => void;
  activeView?: SavedTradeFilterRead;
  onSaveView?: () => void;
  onUpdateView?: () => void;
  onRenameView?: () => void;
  onDeleteView?: () => void;
  isUpdating?: boolean;
}

const TABS: readonly { key: FilterGroupKey; label: string }[] = [
  { key: "trade", label: "Trade" },
  { key: "time", label: "Time" },
  { key: "journal", label: "Journal" },
  { key: "account", label: "Account" },
];

export function TradeFilterSheet({ open, onOpenChange, trigger, filters, renderField, onClear, activeView, onSaveView, onUpdateView, onRenameView, onDeleteView, isUpdating = false }: Props) {
  const [activeGroup, setActiveGroup] = useState<FilterGroupKey>("trade");
  const id = useId();

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => {
      if (nextOpen) setActiveGroup("trade");
      onOpenChange(nextOpen);
    }}>
      {trigger && <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[color-mix(in_srgb,var(--background)_70%,transparent)] lg:hidden" />
        <Dialog.Content className="trade-mobile-contrast fixed inset-x-0 bottom-0 z-50 flex h-[90dvh] max-h-[90dvh] flex-col overflow-hidden rounded-t-2xl border border-border bg-card text-foreground shadow-2xl focus:outline-none lg:hidden">
          <div className="flex shrink-0 items-center justify-between gap-3 px-4 py-3">
            <Dialog.Title className="text-base font-semibold">Filters</Dialog.Title>
            <Dialog.Description className="sr-only">Filters apply immediately. Show results returns to the trade list.</Dialog.Description>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close filters" className="btn-ghost min-h-10 min-w-10 p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>
          <div
            role="tablist"
            aria-label="Filter groups"
            className="mx-3 mb-3 flex shrink-0 gap-1 rounded-xl border border-border bg-secondary p-1"
            onKeyDown={(event) => {
              const currentIndex = TABS.findIndex((tab) => tab.key === activeGroup);
              let nextIndex: number;
              if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % TABS.length;
              else if (event.key === "ArrowLeft") nextIndex = (currentIndex + TABS.length - 1) % TABS.length;
              else if (event.key === "Home") nextIndex = 0;
              else if (event.key === "End") nextIndex = TABS.length - 1;
              else return;
              event.preventDefault();
              setActiveGroup(TABS[nextIndex].key);
              event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[nextIndex]?.focus();
            }}
          >
            {TABS.map((tab) => {
              const count = countActiveFilters(filters, FILTER_GROUPS[tab.key]);
              return (
                <button
                  key={tab.key}
                  id={`${id}-tab-${tab.key}`}
                  type="button"
                  role="tab"
                  aria-selected={activeGroup === tab.key}
                  aria-controls={`${id}-panel-${tab.key}`}
                  tabIndex={activeGroup === tab.key ? 0 : -1}
                  onClick={() => setActiveGroup(tab.key)}
                  className={`flex min-h-10 min-w-0 flex-1 items-center justify-center gap-1 rounded-lg px-1 text-[11px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:text-xs ${activeGroup === tab.key ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {tab.label}
                  {count > 0 && <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 font-mono text-[10px] text-primary-foreground">{count}</span>}
                </button>
              );
            })}
          </div>
          <div id={`${id}-panel-${activeGroup}`} role="tabpanel" aria-labelledby={`${id}-tab-${activeGroup}`} tabIndex={0} className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain border-t border-border p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring">
            {FILTER_GROUPS[activeGroup].map((key) => <Fragment key={key}>{renderField(key)}</Fragment>)}
          </div>
          <div className="shrink-0 space-y-3 border-t border-border p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <div className="flex flex-wrap gap-2">
              {onSaveView && (
                <button type="button" onClick={() => { onOpenChange(false); onSaveView(); }} className="btn-ghost min-h-10 gap-1 px-2 text-xs text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Save className="h-3.5 w-3.5" aria-hidden="true" />Save View
                </button>
              )}
              {activeView?.scope === "USER" && onUpdateView && (
                <button type="button" onClick={onUpdateView} disabled={isUpdating} className="btn-ghost min-h-10 gap-1 px-2 text-xs disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />{isUpdating ? "Updating…" : "Update"}
                </button>
              )}
              {activeView?.scope === "USER" && onRenameView && (
                <button type="button" onClick={() => { onOpenChange(false); onRenameView(); }} className="btn-ghost min-h-10 gap-1 px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Edit2 className="h-3.5 w-3.5" aria-hidden="true" />Rename
                </button>
              )}
              {activeView?.scope === "USER" && onDeleteView && (
                <button type="button" onClick={onDeleteView} className="btn-ghost min-h-10 gap-1 px-2 text-xs text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />Delete View
                </button>
              )}
            </div>
            <div className="flex items-center justify-between gap-3">
              <button type="button" onClick={onClear} className="btn-ghost min-h-10 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Clear all</button>
              <Dialog.Close asChild><button type="button" className="btn-primary min-h-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">Show results</button></Dialog.Close>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
