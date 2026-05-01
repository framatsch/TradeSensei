"use client";

import { useState } from "react";
import type { PatGenerateResponse } from "@/lib/api";
import { GenerateTokenModal } from "@/components/settings/GenerateTokenModal";
import { TokenDisplayModal } from "@/components/settings/TokenDisplayModal";
import { TokenList } from "@/components/settings/TokenList";

export function ApiTokensSettings() {
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<PatGenerateResponse | null>(null);

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
