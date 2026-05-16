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
import { GenerateTokenModal } from "@/components/settings/GenerateTokenModal";
import { TokenDisplayModal } from "@/components/settings/TokenDisplayModal";
import { TokenList } from "@/components/settings/TokenList";

export function ApiTokensSettings() {
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<PatGenerateResponse | null>(null);
  const [showMcpExamples, setShowMcpExamples] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-foreground">API &amp; Tokens</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Generate personal access tokens for MCP integrations and revoke them anytime.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowGenerateModal(true)}
          className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Generate New Token
        </button>
      </div>

      <div className="rounded-md border border-border bg-card">
        <button
          type="button"
          onClick={() => setShowMcpExamples((prev) => !prev)}
          className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-[color-mix(in_srgb,var(--muted)_40%,transparent)]"
          aria-expanded={showMcpExamples}
        >
          <span>What can I do with MCP?</span>
          <span className="text-xs text-muted-foreground">{showMcpExamples ? "Hide" : "Show"}</span>
        </button>
        {showMcpExamples && (
          <div className="space-y-2 border-t border-border px-3 py-3 text-xs text-muted-foreground">
            <ul className="list-disc space-y-1 pl-4">
              <li>
                Performance discovery: "Show me all losing trades from last week where my Mood annotation was below 5."
              </li>
              <li>
                Automated enrichment: "Tag my trades from May 6th 2026 afternoon with Macro Volatility and add a note."
              </li>
              <li>
                Strategy creation: "Create a Breakout Momentum playbook from these rules: ..."
              </li>
              <li>
                Pattern analysis: "What is my win rate on LONG EQUITY trades in the first hour of the day?"
              </li>
            </ul>
            <a
              href="/help#mcp-integration"
              className="text-primary hover:underline"
            >
              Learn more
            </a>
          </div>
        )}
      </div>

      <TokenList />

      {showGenerateModal && (
        <GenerateTokenModal
          onClose={() => setShowGenerateModal(false)}
          onCreated={(token) => setGeneratedToken(token)}
        />
      )}

      {generatedToken && (
        <TokenDisplayModal
          token={generatedToken.token}
          name={generatedToken.name}
          onClose={() => setGeneratedToken(null)}
        />
      )}
    </div>
  );
}
