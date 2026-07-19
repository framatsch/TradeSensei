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
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, ExternalLink, CheckCircle2 } from "lucide-react";
import { toast } from "react-hot-toast";
import {
  getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet,
  startSchwabAuthorizationApiV1BrokerSchwabAuthorizeAccountIdPost,
  completeSchwabConnectionApiV1BrokerSchwabCompleteAccountIdPost,
  disconnectSchwabApiV1BrokerSchwabConnectAccountIdDelete,
} from "@/lib/api/index";
import { extractApiError } from "@/lib/apiErrors";
import type { Account } from "@/lib/types";

interface Props {
  account: Account;
}

export function SchwabConnectSection({ account }: Props) {
  const qc = useQueryClient();
  const [pasteUrl, setPasteUrl] = useState("");
  
  // Status Query
  const { data: statusRes, isLoading: statusLoading } = useQuery({
    queryKey: ["schwabStatus", account.id],
    queryFn: async () => {
      const { data, error } = await getSchwabStatusApiV1BrokerSchwabStatusAccountIdGet({
        path: { account_id: account.id },
      });
      if (error || !data) throw error;
      return data.data;
    },
    refetchInterval: (query) => {
      const isConnected = (query.state.data as any)?.connected;
      return isConnected ? false : 5000;
    },
  });

  const connected = statusRes?.connected ?? false;

  // Authorize Mutation
  const authorizeMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await startSchwabAuthorizationApiV1BrokerSchwabAuthorizeAccountIdPost({
        path: { account_id: account.id },
      });
      if (error || !data) throw error;
      return data.data;
    },
    onSuccess: (data) => {
      window.open(data.authorization_url, "_blank");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to start authorization"));
    },
  });

  // Complete Mutation (Paste mode)
  const completeMutation = useMutation({
    mutationFn: async (url: string) => {
      const { data, error } = await completeSchwabConnectionApiV1BrokerSchwabCompleteAccountIdPost({
        path: { account_id: account.id },
        body: { redirect_url: url },
      });
      if (error || !data) throw error;
      return data.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schwabStatus", account.id] });
      setPasteUrl("");
      toast.success("Schwab account connected");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to complete connection"));
    },
  });

  // Disconnect Mutation
  const disconnectMutation = useMutation({
    mutationFn: async () => {
      const { error } = await disconnectSchwabApiV1BrokerSchwabConnectAccountIdDelete({
        path: { account_id: account.id },
      });
      if (error) throw error;
      return true;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["schwabStatus", account.id] });
      toast.success("Schwab account disconnected");
    },
    onError: (err) => {
      toast.error(extractApiError(err, "Failed to disconnect"));
    },
  });


  if (statusLoading) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-muted-foreground border border-border rounded-lg mt-4">
        <Loader2 className="h-4 w-4 animate-spin" />
        Checking connection status...
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg p-4 mt-4 space-y-4 bg-muted/10">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-foreground">Schwab OAuth Connection</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-[280px]">
            Connect this account to Schwab to enable automatic trade syncing.
          </p>
        </div>
        
        {connected ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium surface-success text-success border">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Connected
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-secondary text-muted-foreground border border-border">
            Disconnected
          </span>
        )}
      </div>

      {!connected && (
        <div className="space-y-4 pt-2">
          <button
            type="button"
            onClick={() => authorizeMutation.mutate()}
            disabled={authorizeMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {authorizeMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
            Connect Schwab
          </button>
          
          <div className="space-y-2 pt-2 border-t border-border/50">
            <label className="block text-xs font-medium text-muted-foreground">
              If the page does not load after you log in, copy the URL and paste it here:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={pasteUrl}
                onChange={(e) => setPasteUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    if (pasteUrl.trim()) completeMutation.mutate(pasteUrl.trim());
                  }
                }}
                placeholder="https://127.0.0.1/?code=...&state=..."
                className="flex-1 px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  if (pasteUrl.trim()) completeMutation.mutate(pasteUrl.trim());
                }}
                disabled={!pasteUrl.trim() || completeMutation.isPending}
                className="px-3 py-2 text-sm font-medium bg-secondary text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors whitespace-nowrap"
              >
                {completeMutation.isPending ? "Submitting..." : "Submit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {connected && (
        <div className="pt-2">
          <button
            type="button"
            onClick={() => disconnectMutation.mutate()}
            disabled={disconnectMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium border border-danger/50 text-danger rounded-md hover:bg-danger/10 disabled:opacity-50 transition-colors"
          >
            {disconnectMutation.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Disconnect
          </button>
          
          <p className="text-xs text-muted-foreground mt-3">
            Note: Schwab refresh tokens expire every 7 days. You will need to click 'Connect Schwab' again when syncing fails with a "reconnect required" message.
          </p>
        </div>
      )}
    </div>
  );
}
