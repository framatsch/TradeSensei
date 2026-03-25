/**
 * SchwabConnectionCard — displays Schwab broker connection status.
 *
 * Shows:
 * - Connected / Not connected status badge
 * - Last sync timestamp (relative)
 * - "Sync Now" button (triggers POST /broker/schwab/sync)
 * - "Disconnect" button (triggers DELETE /broker/schwab/disconnect)
 *
 * When not connected, renders only a placeholder with the ConnectSchwabButton.
 */

"use client";

import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { useSchwabStatus, useSchwabSync, useDisconnectSchwab } from "@/hooks/useSchwabConnection";
import { ConnectSchwabButton } from "./ConnectSchwabButton";
import type { BrokerSyncResult } from "@/lib/types";

export function SchwabConnectionCard() {
  const { data: status, isLoading } = useSchwabStatus();
  const { mutate: syncNow, isPending: isSyncing } = useSchwabSync();
  const { mutate: disconnect, isPending: isDisconnecting } = useDisconnectSchwab();

  const [lastSyncResult, setLastSyncResult] = useState<BrokerSyncResult | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const handleSync = () => {
    setSyncError(null);
    setLastSyncResult(null);
    syncNow(undefined, {
      onSuccess: (result) => setLastSyncResult(result),
      onError: (err) => setSyncError(err.message),
    });
  };

  const handleDisconnect = () => {
    if (window.confirm("Remove Schwab connection? You can reconnect at any time.")) {
      setLastSyncResult(null);
      setSyncError(null);
      disconnect();
    }
  };

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        data-testid="schwab-card-loading"
        className="bg-card rounded-xl border border-border p-6 animate-pulse"
      >
        <div className="h-5 w-32 bg-secondary rounded mb-4" />
        <div className="h-4 w-48 bg-secondary rounded" />
      </div>
    );
  }

  const connected = status?.connected ?? false;
  const lastSyncAt = status?.last_sync_at;

  return (
    <div
      data-testid="schwab-connection-card"
      className="bg-card rounded-xl border border-border p-6 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Schwab brand mark */}
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-secondary text-white font-bold text-lg">
            S
          </div>
          <div>
            <h3 className="text-foreground font-semibold text-base">Schwab</h3>
            <p className="text-muted-foreground text-xs">Charles Schwab brokerage</p>
          </div>
        </div>

        {/* Status badge */}
        <span
          data-testid={connected ? "status-connected" : "status-disconnected"}
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
            connected
              ? "bg-green-900/40 text-green-400 border border-green-700/40"
              : "bg-secondary text-muted-foreground border border-border dark:border-border"
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-green-400" : "bg-zinc-500"}`}
          />
          {connected ? "Connected" : "Not connected"}
        </span>
      </div>

      {/* Connected state */}
      {connected && (
        <>
          {/* Last sync info */}
          <div className="text-sm text-muted-foreground">
            {lastSyncAt ? (
              <span data-testid="last-sync-time">
                Last synced{" "}
                <span className="text-muted-foreground">
                  {formatDistanceToNow(new Date(lastSyncAt), { addSuffix: true })}
                </span>
              </span>
            ) : (
              <span data-testid="never-synced">Never synced</span>
            )}
          </div>

          {/* Last sync result */}
          {lastSyncResult && (
            <div
              data-testid="sync-result"
              className="bg-secondary/50 rounded-lg px-4 py-3 text-sm space-y-1"
            >
              <p className="text-green-400 font-medium">
                {lastSyncResult.imported_count} trade
                {lastSyncResult.imported_count !== 1 ? "s" : ""} imported
              </p>
              {lastSyncResult.skipped_count > 0 && (
                <p className="text-muted-foreground">{lastSyncResult.skipped_count} skipped (duplicates)</p>
              )}
              {lastSyncResult.errors.length > 0 && (
                <ul className="text-red-400 mt-1 space-y-0.5">
                  {lastSyncResult.errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Sync error */}
          {syncError && (
            <p data-testid="sync-error" className="text-red-400 text-sm">
              {syncError}
            </p>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handleSync}
              disabled={isSyncing}
              data-testid="sync-button"
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              {isSyncing ? (
                <>
                  <svg
                    className="animate-spin w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  Syncing…
                </>
              ) : (
                <>
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="w-4 h-4"
                  >
                    <polyline points="1 4 1 10 7 10" />
                    <path d="M3.51 15a9 9 0 1 0 .49-4.98" />
                  </svg>
                  Sync Now
                </>
              )}
            </button>

            <button
              onClick={handleDisconnect}
              disabled={isDisconnecting}
              data-testid="disconnect-button"
              className="inline-flex items-center gap-2 px-4 py-2 bg-transparent hover:bg-red-900/30 disabled:opacity-50 disabled:cursor-not-allowed text-red-400 hover:text-red-300 text-sm font-medium rounded-lg border border-red-800/40 hover:border-red-700/60 transition-colors"
            >
              {isDisconnecting ? "Disconnecting…" : "Disconnect"}
            </button>
          </div>
        </>
      )}

      {/* Disconnected state */}
      {!connected && (
        <div className="space-y-3">
          <p className="text-muted-foreground text-sm">
            Connect your Schwab account to automatically import trades via OAuth.
          </p>
          <ConnectSchwabButton />
        </div>
      )}
    </div>
  );
}
