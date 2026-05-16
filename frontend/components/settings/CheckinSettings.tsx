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

/**
 * CheckinSettings — manage MarketIndexDefinition
 * entities from the global settings module.
 */

"use client";

import { useState } from "react";
import {
  useMarketIndexes,
  useCreateMarketIndex,
  useUpdateMarketIndex,
  useDeleteMarketIndex,
} from "@/hooks/useCheckinDefinitions";
import type {
  MarketIndexDefinitionResponse,
  MarketIndexDefinitionCreate,
  MarketIndexDefinitionUpdate,
} from "@/lib/api/types.gen";

// ─── Market Indexes Section ──────────────────────────────────────────────────

function StatusToggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 ${
        enabled ? "bg-primary" : "bg-muted"
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-150 ${
          enabled ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

function MarketIndexesSection() {
  const { data: indexes, isLoading, isError } = useMarketIndexes();
  const createMutation = useCreateMarketIndex();
  const updateMutation = useUpdateMarketIndex();
  const deleteMutation = useDeleteMarketIndex();

  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [tradingviewUrl, setTradingviewUrl] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editSymbol, setEditSymbol] = useState("");
  const [editName, setEditName] = useState("");
  const [editTradingviewUrl, setEditTradingviewUrl] = useState("");

  function handleCreate() {
    const payload: MarketIndexDefinitionCreate = {
      symbol: symbol.trim().toUpperCase(),
      name: name.trim(),
      tradingview_url: tradingviewUrl.trim() || null,
      is_active: true,
    };
    createMutation.mutate(payload, {
      onSuccess: () => {
        setSymbol("");
        setName("");
        setTradingviewUrl("");
      },
    });
  }

  function handleToggleActive(id: string, current: boolean) {
    const payload: MarketIndexDefinitionUpdate = {
      is_active: !current,
    };
    updateMutation.mutate({ id, payload });
  }

  function startEdit(index: MarketIndexDefinitionResponse) {
    setEditingId(index.id);
    setEditSymbol(index.symbol);
    setEditName(index.name);
    setEditTradingviewUrl(index.tradingview_url ?? "");
  }

  function cancelEdit() {
    setEditingId(null);
  }

  function saveEdit(id: string) {
    const payload: MarketIndexDefinitionUpdate = {
      symbol: editSymbol.trim().toUpperCase(),
      name: editName.trim(),
      tradingview_url: editTradingviewUrl.trim() || null,
    };
    updateMutation.mutate(
      { id, payload },
      { onSuccess: () => setEditingId(null) }
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">MARKET INDEXES</h3>
        <p className="text-xs text-muted-foreground mt-0.5">
          Manage index definitions used in check-ins.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          placeholder="Symbol (e.g. SPX)"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
        <input
          value={tradingviewUrl}
          onChange={(e) => setTradingviewUrl(e.target.value)}
          placeholder="TradingView URL"
          className="w-full px-3 py-2 rounded-lg border border-border bg-card text-foreground text-sm"
        />
      </div>
      <button
        type="button"
        onClick={handleCreate}
        disabled={createMutation.isPending || !symbol.trim() || !name.trim()}
        className="px-4 py-2 rounded-lg text-sm font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground transition-colors"
      >
        {createMutation.isPending ? "Creating..." : "Add Market Index"}
      </button>

      {isLoading ? (
        <div className="py-4 text-sm text-muted-foreground">Loading indexes...</div>
      ) : isError ? (
        <div className="py-4 text-sm text-destructive">Could not load market indexes.</div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">TradingView</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(indexes ?? []).map((index) => (
                <tr key={index.id} className="bg-card hover:bg-muted/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-sm text-muted-foreground">
                    {editingId === index.id ? (
                      <input
                        value={editSymbol}
                        onChange={(e) => setEditSymbol(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : (
                      index.symbol
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editingId === index.id ? (
                      <input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : (
                      index.name
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editingId === index.id ? (
                      <input
                        value={editTradingviewUrl}
                        onChange={(e) => setEditTradingviewUrl(e.target.value)}
                        className="w-full px-2 py-1 rounded border border-border bg-background text-foreground text-sm"
                      />
                    ) : index.tradingview_url ? (
                      <a
                        href={index.tradingview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline"
                      >
                        Open
                      </a>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <StatusToggle
                      enabled={index.is_active ?? false}
                      onChange={() => handleToggleActive(index.id, index.is_active ?? false)}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-3">
                      {editingId === index.id ? (
                        <>
                          <button
                            type="button"
                            onClick={() => saveEdit(index.id)}
                            className="text-xs font-medium text-primary hover:underline"
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            className="text-xs text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => startEdit(index)}
                          className="text-xs font-medium text-muted-foreground hover:text-foreground"
                        >
                          Edit
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => deleteMutation.mutate(index.id)}
                        className="text-xs text-destructive hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Exported component ───────────────────────────────────────────────────────

export function CheckinSettings() {
  return (
    <div className="space-y-8">
      <MarketIndexesSection />
    </div>
  );
}
