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

import { useEffect, useState, useId } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { X, Loader2, AlertTriangle, Trash2, Eye, EyeOff } from "lucide-react";
import { toast } from "react-hot-toast";
import { client } from "@/lib/api/client.gen";
import { 
  updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch, 
  deleteAccountApiV1PortfoliosPortfolioIdAccountsAccountIdDelete,
  clearAccountTradesApiV1PortfoliosPortfolioIdAccountsAccountIdTradesDelete,
  getAccountCredentialsApiV1PortfoliosPortfolioIdAccountsAccountIdCredentialsGet
} from "@/lib/api/index";
import { extractApiError } from "@/lib/apiErrors";
import type { Account, AccountType } from "@/lib/types";
import { SchwabConnectSection } from "./SchwabConnectSection";

const BROKER_TYPE_LABELS: Record<string, string> = {
  ibkr: "IBKR",
  schwab: "Schwab",
  manual: "Manual",
};

const BROKER_TYPE_BADGES: Record<string, string> = {
  ibkr: "bg-indigo-900/30 text-indigo-400 border border-indigo-800",
  schwab: "bg-blue-900/30 text-blue-400 border border-blue-800",
  manual: "bg-secondary text-muted-foreground border border-border",
};

const CREDENTIAL_FIELDS: Record<Exclude<AccountType, "manual">, { key: string; label: string }[]> = {
  schwab: [
    { key: "schwab_app_key", label: "App Key" },
    { key: "schwab_app_secret", label: "App Secret" },
  ],
  ibkr: [
    { key: "ibkr_flex_token", label: "Flex Token" },
    { key: "ibkr_flex_query_id", label: "Flex Query ID" },
  ],
};

const INPUT_CLASS =
  "w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/50";
const LABEL_CLASS = "block text-xs font-medium text-muted-foreground mb-1";

interface Props {
  account: Account;
  onClose: () => void;
}

export function BrokerAccountEditModal({ account, onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState(account.name);
  const [accountNumber, setAccountNumber] = useState(account.account_number ?? "");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [testMessage, setTestMessage] = useState("");
  const [testing, setTesting] = useState(false);
  const [togglingActive, setTogglingActive] = useState(false);
  const [isActive, setIsActive] = useState(account.is_active);
  const [showDangerZone, setShowDangerZone] = useState(false);
  const [showCredentials, setShowCredentials] = useState<Record<string, boolean>>({});
  
  const [confirmName, setConfirmName] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Clear trades state
  const [clearConfirmName, setClearConfirmName] = useState("");
  const [clearError, setClearError] = useState<string | null>(null);
  const [isClearing, setIsClearing] = useState(false);

  const uid = useId();

  const portfolioId = account.portfolio_id;

  useEffect(() => {
    let cancelled = false;
    if (!portfolioId || account.type === "manual") {
      setCredentials({});
      return;
    }

    const loadCredentials = async () => {
      const { data, error: fetchErr } = await getAccountCredentialsApiV1PortfoliosPortfolioIdAccountsAccountIdCredentialsGet({
        path: { portfolio_id: portfolioId, account_id: account.id }
      });

      if (cancelled) {
        return;
      }

      if (fetchErr || !data?.data?.properties) {
        setCredentials({});
        return;
      }

      const normalized = Object.fromEntries(
        Object.entries(data.data.properties).map(([key, value]) => [key.toLowerCase(), value as string])
      );
      setCredentials(normalized);
    };

    void loadCredentials();

    return () => {
      cancelled = true;
    };
  }, [account.id, account.type, portfolioId]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      const filledCredentials = Object.fromEntries(
        Object.entries(credentials).filter(([, v]) => v.trim() !== "")
      );
      const payload: any = {
        name: name.trim(),
        account_number: accountNumber.trim() || null,
      };
      if (Object.keys(filledCredentials).length > 0) {
        payload.properties = filledCredentials;
      }

      if (!portfolioId) throw new Error("Account must belong to a portfolio");

      const { data, error: err } = await updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch({
        path: { 
          portfolio_id: portfolioId, 
          account_id: account.id 
        },
        body: payload,
      });
      if (err || !data) throw err ?? new Error("Failed to update account");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account updated");
      onClose();
    },
    onError: (err: any) => {
      setError(extractApiError(err, "Failed to update account"));
    },
  });

  const handleToggleActive = () => {
    if (!portfolioId) {
      toast.error("Account must belong to a portfolio");
      return;
    }
    setTogglingActive(true);

    updateAccountApiV1PortfoliosPortfolioIdAccountsAccountIdPatch({
      path: { portfolio_id: portfolioId, account_id: account.id },
      body: { is_active: !isActive } as any,
    })
      .then(({ error: patchErr }) => {
        if (patchErr) throw patchErr;
        qc.invalidateQueries({ queryKey: ["accounts"] });
        qc.invalidateQueries({ queryKey: ["portfolios"] });
        
        setIsActive(!isActive);
        toast.success(!isActive ? "Account reactivated" : "Account deactivated");
      })
      .catch((patchErr: unknown) => {
        toast.error(extractApiError(patchErr, "Failed to update account status"));
      })
      .finally(() => {
        setTogglingActive(false);
      });
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setTestMessage("");

    try {
      const credValues = account.type !== "manual"
        ? Object.fromEntries(
            Object.entries(credentials).filter(([, v]) => v.trim() !== "")
          )
        : {};

      const { error: testErr } = await client.post<unknown, unknown, false>({
        url: `/api/v1/portfolios/${portfolioId}/accounts/test-connection`,
        body: {
          type: account.type,
          properties: Object.keys(credValues).length > 0 ? credValues : null,
          account_id: account.id,
        },
      });

      if (testErr) {
        const status = (testErr as any)?.status;
        if (status === 404 || status === 405) {
          setTestResult("error");
          setTestMessage("Connection test unavailable");
        } else {
          setTestResult("error");
          setTestMessage(extractApiError(testErr, "Connection test failed"));
        }
      } else {
        setTestResult("success");
        setTestMessage("Connection successful");
      }
    } catch {
      setTestResult("error");
      setTestMessage("Connection test failed");
    } finally {
      setTesting(false);
    }
  };

  const handleCredentialChange = (key: string, value: string) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    updateMutation.mutate();
  };

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (!portfolioId) throw new Error("Account must belong to a portfolio");
      const { error: err } = await deleteAccountApiV1PortfoliosPortfolioIdAccountsAccountIdDelete({
        path: {
          portfolio_id: portfolioId,
          account_id: account.id,
        },
      });
      if (err) throw err;
      return true;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      toast.success("Account deleted");
      onClose();
    },
    onError: (err: any) => {
      setDeleteError(extractApiError(err, "Failed to delete account"));
    },
  });

  const handleDelete = () => {
    if (confirmName.trim() !== account.name) return;
    setDeleteError(null);
    deleteMutation.mutate();
  };

  const handleClearTrades = async () => {
    if (clearConfirmName.trim() !== account.name) return;
    if (!portfolioId) {
      setClearError("Account must belong to a portfolio");
      return;
    }
    setClearError(null);
    setIsClearing(true);
    try {
      const { data, error: clearErr } =
        await clearAccountTradesApiV1PortfoliosPortfolioIdAccountsAccountIdTradesDelete({
          path: { portfolio_id: portfolioId, account_id: account.id },
          query: { acknowledged: true },
        });
      if (clearErr || !data) throw clearErr ?? new Error("Failed to clear trades");
      const result = (data as any).data;
      qc.invalidateQueries({ queryKey: ["trades"] });
      qc.invalidateQueries({ queryKey: ["metrics"] });
      qc.invalidateQueries({ queryKey: ["tax"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      toast.success(
        `Cleared ${result.trades_deleted} trades and ${result.executions_deleted} executions.`,
      );
      setClearConfirmName("");
      onClose();
    } catch (err: any) {
      setClearError(extractApiError(err, "Failed to clear trades"));
    } finally {
      setIsClearing(false);
    }
  };

  const credentialFields = account.type !== "manual" ? CREDENTIAL_FIELDS[account.type] : null;
  const brokerBadge = BROKER_TYPE_BADGES[account.type] || BROKER_TYPE_BADGES.manual;
  const canSubmit = name.trim().length > 0 && !updateMutation.isPending;
  const canDelete = confirmName.trim() === account.name && !deleteMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm overflow-y-auto">
      <div className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Edit Account</h3>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor={`${uid}-name`} className={LABEL_CLASS}>
              Display Name
            </label>
            <input
              id={`${uid}-name`}
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={INPUT_CLASS}
              data-testid="edit-account-name-input"
            />
          </div>

          <div>
            <label className={LABEL_CLASS}>Broker Type</label>
            <span
              className={`inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium ${brokerBadge}`}
              data-testid="immutable-broker-type"
            >
              {BROKER_TYPE_LABELS[account.type] || "Manual"}
            </span>
          </div>

          {(account.type === "ibkr" || account.type === "schwab") && (
            <div>
              <label htmlFor={`${uid}-account-number`} className={LABEL_CLASS}>
                Account Number
              </label>
              <input
                id={`${uid}-account-number`}
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder={account.type === "ibkr" ? "e.g. U1234567" : "e.g. 12345678"}
                className={INPUT_CLASS}
                data-testid="edit-account-number-input"
              />
            </div>
          )}

          {credentialFields && (
            <div className="border border-border rounded-lg p-4 space-y-3">
              <div>
                <p className="text-xs font-semibold text-muted-foreground">API Credentials</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Stored credentials are loaded for review and can be edited.
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {credentialFields.map((field) => (
                  <div key={field.key}>
                    <label htmlFor={`cred-${field.key}`} className={LABEL_CLASS}>
                      {field.label}
                    </label>
                    <div className="relative">
                      <input
                        id={`cred-${field.key}`}
                        type={showCredentials[field.key] ? "text" : "password"}
                        autoComplete="off"
                        value={credentials[field.key] ?? ""}
                        onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                        placeholder=""
                        className={`${INPUT_CLASS} pr-10`}
                        data-testid={`credential-${field.key}`}
                      />
                      <button
                        type="button"
                        onClick={() =>
                          setShowCredentials((prev) => ({
                            ...prev,
                            [field.key]: !prev[field.key],
                          }))
                        }
                        className="absolute inset-y-0 right-0 px-2 text-muted-foreground hover:text-foreground"
                        aria-label={showCredentials[field.key] ? `Hide ${field.label}` : `Show ${field.label}`}
                        data-testid={`toggle-credential-${field.key}`}
                      >
                        {showCredentials[field.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-1">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/50 disabled:opacity-50 transition-colors text-foreground"
                  data-testid="edit-test-connection-button"
                >
                  {testing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Test Connection
                </button>
                {testResult === "success" && (
                  <p className="mt-2 text-xs text-emerald-400" data-testid="edit-test-connection-success">
                    {testMessage}
                  </p>
                )}
                {testResult === "error" && (
                  <p className="mt-2 text-xs text-danger" data-testid="edit-test-connection-error">
                    {testMessage}
                  </p>
                )}
              </div>
            </div>
          )}

          {account.type === "schwab" && <SchwabConnectSection account={account} />}

          <div className="border-t border-border pt-4 space-y-2">
            <p className="text-xs font-semibold text-muted-foreground">Status</p>
            {isActive ? (
              <div className="space-y-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-900/50 text-emerald-400 border border-emerald-800">
                  Active
                </span>
                <button
                  type="button"
                  onClick={handleToggleActive}
                  disabled={togglingActive}
                  className="block text-sm text-danger hover:text-danger/80 transition-colors disabled:opacity-50"
                  data-testid="deactivate-button"
                >
                  {togglingActive ? "Deactivating..." : "Deactivate Account"}
                </button>
                <p className="text-xs text-muted-foreground">Stops data sync, but retains all historical trades</p>
              </div>
            ) : (
              <div className="space-y-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-secondary text-muted-foreground border border-border">
                  Inactive
                </span>
                <button
                  type="button"
                  onClick={handleToggleActive}
                  disabled={togglingActive}
                  className="block text-sm text-primary hover:text-primary/80 transition-colors disabled:opacity-50"
                  data-testid="reactivate-button"
                >
                  {togglingActive ? "Reactivating..." : "Reactivate Account"}
                </button>
              </div>
            )}
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="edit-account-error">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={updateMutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              data-testid="save-edit-account"
            >
              {updateMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>

        <div className="border-t border-border pt-5">
          <button
            onClick={() => setShowDangerZone(!showDangerZone)}
            className="flex items-center gap-2 text-danger hover:text-danger/80 transition-colors text-sm font-semibold w-full text-left"
          >
            <AlertTriangle className="h-4 w-4" />
            {showDangerZone ? "Hide Danger Zone" : "Show Danger Zone"}
          </button>

          {showDangerZone && (
            <div className="mt-4 bg-danger/5 border border-danger/20 rounded-md p-4 space-y-5 animate-in fade-in slide-in-from-top-2 duration-200" data-testid="account-danger-zone">

              {/* Clear all trades */}
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-danger">Clear All Trades</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Permanently deletes all trades, executions, and broker raw transactions for this account. The account itself remains. This cannot be undone.
                  </p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm text-foreground font-medium">
                    Type <span className="font-bold text-danger select-none">{account.name}</span> to confirm:
                  </label>
                  <input
                    type="text"
                    value={clearConfirmName}
                    onChange={(e) => setClearConfirmName(e.target.value)}
                    disabled={isClearing}
                    placeholder={account.name}
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger text-foreground"
                    data-testid="clear-trades-confirm-input"
                  />
                </div>
                {clearError && (
                  <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="clear-trades-error">
                    {clearError}
                  </p>
                )}
                <button
                  onClick={handleClearTrades}
                  disabled={clearConfirmName.trim() !== account.name || isClearing}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-danger text-white rounded-md hover:bg-danger/90 disabled:opacity-50 transition-colors"
                  data-testid="clear-trades-button"
                >
                  <Trash2 className="h-4 w-4" />
                  {isClearing ? "Clearing..." : "Clear All Trades"}
                </button>
              </div>

              {/* Divider */}
              <div className="border-t border-danger/20" />

              {/* Delete account */}
              <div className="space-y-3">
                <p className="text-sm text-danger">
                  This will permanently delete this account, all associated trades, and cash transactions. This action cannot be undone.
                </p>

                <div className="space-y-1.5">
                  <label className="text-sm text-foreground font-medium">
                    Type <span className="font-bold text-danger select-none">{account.name}</span> to confirm:
                  </label>
                  <input
                    type="text"
                    value={confirmName}
                    onChange={(e) => setConfirmName(e.target.value)}
                    disabled={deleteMutation.isPending}
                    placeholder={account.name}
                    className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger text-foreground"
                    data-testid="delete-confirm-input"
                  />
                </div>

                {deleteError && (
                  <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="delete-error">
                    {deleteError}
                  </p>
                )}

                <button
                  onClick={handleDelete}
                  disabled={!canDelete}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-danger text-white rounded-md hover:bg-danger/90 disabled:opacity-50 transition-colors"
                  data-testid="delete-account-button"
                >
                  <Trash2 className="h-4 w-4" />
                  {deleteMutation.isPending ? "Deleting..." : "Delete Account"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
