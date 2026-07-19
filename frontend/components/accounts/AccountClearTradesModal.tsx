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

import { useState, useId } from "react";
import { X, AlertTriangle, Trash2 } from "lucide-react";
import type { Account } from "@/lib/types";

interface Props {
  account: Account;
  onClose: () => void;
  onClearTrades: (accountId: string) => void;
  isClearing: boolean;
}

export function AccountClearTradesModal({ account, onClose, onClearTrades, isClearing }: Props) {
  const [confirmName, setConfirmName] = useState("");
  const uid = useId();

  const handleClear = () => {
    if (confirmName.trim() !== account.name) return;
    onClearTrades(account.id);
  };

  const canClear = confirmName.trim() === account.name && !isClearing;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm overflow-y-auto">
      <div 
        className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${uid}-title`}
      >
        <div className="flex items-center justify-between">
          <h3 id={`${uid}-title`} className="text-lg font-semibold text-foreground">Clear All Trades</h3>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2 text-danger">
            <AlertTriangle className="h-5 w-5" />
            <h4 className="text-sm font-semibold">Danger Zone</h4>
          </div>

          <div className="bg-danger/5 border border-danger/20 rounded-md p-4 space-y-3" data-testid="danger-zone-clear-trades">
            <p className="text-sm text-danger">
              This will permanently delete <strong>all</strong> trades, executions, and broker raw transactions for{" "}
              <span className="font-semibold">{account.name}</span>. The account itself will not be deleted. This action cannot be undone.
            </p>

            <div className="space-y-1.5">
              <label htmlFor={`${uid}-confirm`} className="text-sm text-foreground font-medium">
                Type <span className="font-bold text-danger select-none">{account.name}</span> to confirm:
              </label>
              <input
                id={`${uid}-confirm`}
                type="text"
                value={confirmName}
                onChange={(e) => setConfirmName(e.target.value)}
                disabled={isClearing}
                placeholder={account.name}
                className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger text-foreground"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isClearing}
                className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleClear}
                disabled={!canClear}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-danger text-white rounded-md hover:bg-danger/90 disabled:opacity-50 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                {isClearing ? "Clearing..." : "Clear All Trades"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
