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
import type { PatGenerateResponse } from "@/lib/api";
import { useCreateApiToken } from "@/hooks/useApiTokens";

interface GenerateTokenModalProps {
  onClose: () => void;
  onCreated: (token: PatGenerateResponse) => void;
}

type ExpirationOption = "30" | "90" | "365" | "none";

function buildExpiresAt(option: ExpirationOption): string | null {
  if (option === "none") return null;
  const days = Number.parseInt(option, 10);
  const now = new Date();
  const expires = new Date(now.getTime() + days * 24 * 60 * 60 * 1000);
  return expires.toISOString();
}

export function GenerateTokenModal({ onClose, onCreated }: GenerateTokenModalProps) {
  const [name, setName] = useState("");
  const [expiration, setExpiration] = useState<ExpirationOption>("90");
  const [error, setError] = useState<string | null>(null);
  const createMutation = useCreateApiToken();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError("Token name is required.");
      return;
    }

    setError(null);
    try {
      const created = await createMutation.mutateAsync({
        name: trimmedName,
        expires_at: buildExpiresAt(expiration),
      });
      onCreated(created);
      onClose();
    } catch {
      setError("Failed to generate token.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-foreground">Generate New Token</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Create a personal access token for MCP clients.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-foreground" htmlFor="token-name">
              Name
            </label>
            <input
              id="token-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Claude Desktop"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label
              className="mb-1 block text-sm font-medium text-foreground"
              htmlFor="token-expiration"
            >
              Expiration
            </label>
            <select
              id="token-expiration"
              value={expiration}
              onChange={(e) => setExpiration(e.target.value as ExpirationOption)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="30">30 days</option>
              <option value="90">90 days</option>
              <option value="365">1 year</option>
              <option value="none">No expiration</option>
            </select>
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createMutation.isPending ? "Generating..." : "Generate"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
