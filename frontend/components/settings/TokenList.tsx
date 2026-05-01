"use client";

import { useApiTokens, useRevokeApiToken } from "@/hooks/useApiTokens";
import type { PatRead } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";

function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function getStatus(token: PatRead): "Active" | "Expired" | "Revoked" {
  if (token.is_revoked) return "Revoked";
  if (token.expires_at && new Date(token.expires_at).getTime() < Date.now()) {
    return "Expired";
  }
  return "Active";
}

export function TokenList() {
  const { data: tokens, isLoading, isError, error } = useApiTokens();
  const revokeMutation = useRevokeApiToken();

  const handleRevoke = async (token: PatRead) => {
    if (getStatus(token) !== "Active") return;
    const confirmed = window.confirm(`Revoke token "${token.name}"?`);
    if (!confirmed) return;
    await revokeMutation.mutateAsync(token.id);
  };

  if (isLoading) {
    return (
      <div className="flex h-36 items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  if (isError) {
    return <p className="text-sm text-danger">{error.message || "Failed to load tokens."}</p>;
  }

  if (!tokens?.length) {
    return (
      <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
        No tokens yet. Generate your first token to connect MCP clients.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="min-w-full divide-y divide-border text-sm">
        <thead className="bg-card">
          <tr>
            <th className="px-3 py-2 text-left font-medium text-foreground">Name</th>
            <th className="px-3 py-2 text-left font-medium text-foreground">Created</th>
            <th className="px-3 py-2 text-left font-medium text-foreground">Expires</th>
            <th className="px-3 py-2 text-left font-medium text-foreground">Last Used</th>
            <th className="px-3 py-2 text-left font-medium text-foreground">Status</th>
            <th className="px-3 py-2 text-left font-medium text-foreground">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border bg-background">
          {tokens.map((token) => {
            const status = getStatus(token);
            return (
              <tr key={token.id}>
                <td className="px-3 py-2 text-foreground">{token.name}</td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(token.created_at)}</td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(token.expires_at)}</td>
                <td className="px-3 py-2 text-muted-foreground">{formatDate(token.last_used_at)}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      status === "Active"
                        ? "bg-emerald-500/15 text-emerald-500"
                        : status === "Expired"
                          ? "bg-amber-500/15 text-amber-500"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {status}
                  </span>
                </td>
                <td className="px-3 py-2">
                  {status === "Active" ? (
                    <button
                      type="button"
                      onClick={() => void handleRevoke(token)}
                      className="text-xs font-medium text-danger hover:underline"
                    >
                      Revoke
                    </button>
                  ) : (
                    <span className="text-xs text-muted-foreground">-</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
