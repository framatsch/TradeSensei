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

import { useState } from "react";
import { useCreateSavedTradeFilter } from "@/hooks/useSavedTradeFilters";
import type { TradeFilters } from "@/hooks/useTrades";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  currentFilters: TradeFilters;
}

export function SaveFilterModal({ isOpen, onClose, currentFilters }: Props) {
  const [name, setName] = useState("");
  const createFilter = useCreateSavedTradeFilter();

  if (!isOpen) return null;

  const handleSave = () => {
    if (!name.trim()) return;

    // Filter out empty values to keep the definition clean
    const definition = Object.fromEntries(
      Object.entries(currentFilters).filter(([, value]) => {
        if (Array.isArray(value)) return value.length > 0;
        return value !== "" && value !== null && value !== undefined;
      })
    );

    createFilter.mutate(
      {
        name: name.trim(),
        definition,
      },
      {
        onSuccess: () => {
          setName("");
          onClose();
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md panel-float p-6">
        <h2 className="mb-4 text-xl font-bold text-foreground">Save Current View</h2>
        
        <div className="mb-6">
          <label className="mb-2 block text-sm font-medium text-foreground">
            View Name
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-input bg-secondary px-4 py-2 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="e.g. My Winning Tech Shorts"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            autoFocus
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || createFilter.isPending}
            className="btn-primary disabled:opacity-50"
          >
            {createFilter.isPending ? "Saving..." : "Save View"}
          </button>
        </div>
      </div>
    </div>
  );
}
