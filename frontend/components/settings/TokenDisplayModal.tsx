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

interface TokenDisplayModalProps {
  token: string;
  name: string;
  onClose: () => void;
}

export function TokenDisplayModal({ token, name, onClose }: TokenDisplayModalProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(token);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-lg border border-border bg-background p-6 shadow-xl">
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground">Token Created</h3>
          <p className="text-sm text-muted-foreground">
            Save this token now. You will not be able to see it again.
          </p>
          <p className="text-xs text-amber-500">
            Token name: <span className="font-medium text-foreground">{name}</span>
          </p>
        </div>

        <div className="mt-4 rounded-md border border-border bg-card p-3">
          <code className="block break-all text-xs text-foreground">{token}</code>
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
