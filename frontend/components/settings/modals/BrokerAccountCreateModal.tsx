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
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { X, Loader2, Eye, EyeOff } from "lucide-react";
import { toast } from "react-hot-toast";
import { client } from "@/lib/api/client.gen";
import { createAccountApiV1PortfoliosPortfolioIdAccountsPost } from "@/lib/api/index";
import { extractApiError } from "@/lib/apiErrors";
import type { Account, AccountType } from "@/lib/types";
import type { AccountCreate } from "@/lib/api/types.gen";

const BROKER_TYPE_OPTIONS: { value: AccountType; label: string }[] = [
  { value: "manual", label: "Manual" },
  { value: "schwab", label: "Charles Schwab" },
  { value: "ibkr", label: "Interactive Brokers (IBKR)" },
];

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
  portfolioId: string;
  portfolioName: string;
  onClose: () => void;
}

export function BrokerAccountCreateModal({ portfolioId, portfolioName, onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [accountNumber, setAccountNumber] = useState("");
  const [type, setType] = useState<AccountType>("ibkr");
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [syncStartDate, setSyncStartDate] = useState(`${new Date().getFullYear()}-01-01`);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [testMessage, setTestMessage] = useState("");
  const [testing, setTesting] = useState(false);
  const [showCredentials, setShowCredentials] = useState<Record<string, boolean>>({});
  const uid = useId();

  const createMutation = useMutation({
    mutationFn: async () => {
      const filledCredentials = Object.fromEntries(
        Object.entries(credentials).filter(([, v]) => v.trim() !== "")
      );
      const properties = Object.keys(filledCredentials).length > 0 ? filledCredentials : null;

      const payload: AccountCreate = {
        name: name.trim(),
        account_number: accountNumber.trim() || undefined,
        type,
        properties,
        portfolio_id: portfolioId,
        settings: {
          sync_days: 30,
          flex_from_date_preset: "ytd" as const,
          flex_custom_from_date: syncStartDate.replace(/-/g, ""),
        },
      };

      const { data, error: err } = await createAccountApiV1PortfoliosPortfolioIdAccountsPost({
        path: { portfolio_id: portfolioId },
        body: payload,
      });
      if (err || !data) throw err ?? new Error("Failed to create account");
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts", portfolioId] });
      qc.invalidateQueries({ queryKey: ["portfolios"] });
      toast.success("Account created");
      onClose();
    },
    onError: (err: unknown) => {
      setError(extractApiError(err, "Failed to create account"));
    },
  });

  const handleCredentialChange = (key: string, value: string) => {
    setCredentials((prev) => ({ ...prev, [key]: value }));
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    setTestMessage("");

    try {
      const credValues = type !== "manual"
        ? Object.fromEntries(
            Object.entries(credentials).filter(([, v]) => v.trim() !== "")
          )
        : {};

      const { error: testErr } = await client.post<unknown, unknown, false>({
        url: `/api/v1/portfolios/${portfolioId}/accounts/test-connection`,
        body: {
          type,
          properties: Object.keys(credValues).length > 0 ? credValues : null,
        },
      });

      if (testErr) {
        const status = typeof testErr === "object" && "status" in testErr ? testErr.status : undefined;
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    createMutation.mutate();
  };

  const credentialFields = type !== "manual" ? CREDENTIAL_FIELDS[type] : null;
  const canSubmit = name.trim().length > 0 && !createMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm overflow-y-auto">
      <div className="bg-background rounded-lg border border-border shadow-xl max-w-md w-full p-6 space-y-5 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">Create Broker Account</h3>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted/50 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="inline-flex items-center px-3 py-1.5 bg-muted/50 border border-border rounded-md">
          <span className="text-sm text-muted-foreground">
            Target Portfolio: <span className="font-medium text-foreground">{portfolioName}</span>
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor={`${uid}-name`} className={LABEL_CLASS}>
              Display Name <span className="text-danger">*</span>
            </label>
            <input
              id={`${uid}-name`}
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My IBKR Account"
              className={INPUT_CLASS}
              data-testid="account-name-input"
            />
          </div>

          <div>
            <label htmlFor={`${uid}-type`} className={LABEL_CLASS}>
              Broker Type
            </label>
            <select
              id={`${uid}-type`}
              value={type}
              onChange={(e) => {
                setType(e.target.value as AccountType);
                setCredentials({});
              }}
              className={INPUT_CLASS}
              data-testid="broker-type-select"
            >
              {BROKER_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {(type === "ibkr" || type === "schwab") && (
            <div>
              <label htmlFor={`${uid}-account-number`} className={LABEL_CLASS}>
                Account Number
              </label>
              <input
                id={`${uid}-account-number`}
                type="text"
                value={accountNumber}
                onChange={(e) => setAccountNumber(e.target.value)}
                placeholder={type === "ibkr" ? "e.g. U1234567" : "e.g. 12345678"}
                className={INPUT_CLASS}
                data-testid="account-number-input"
              />
            </div>
          )}

          {credentialFields && (
            <div className="border border-border rounded-lg p-4 space-y-3">
              <div>
                <p className="text-xs font-semibold text-muted-foreground">API Credentials</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Credentials are encrypted before storage and never returned in plain text.
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
                  data-testid="test-connection-button"
                >
                  {testing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Test Connection
                </button>
                {testResult === "success" && (
                  <p className="mt-2 text-xs text-emerald-400" data-testid="test-connection-success">
                    {testMessage}
                  </p>
                )}
                {testResult === "error" && (
                  <p className="mt-2 text-xs text-danger" data-testid="test-connection-error">
                    {testMessage}
                  </p>
                )}
              </div>
            </div>
          )}

          {type === "manual" && (
            <div className="border border-border rounded-lg p-4">
              <p className="text-xs text-muted-foreground">No credentials required for manual accounts</p>
            </div>
          )}

          <div className="border border-border rounded-lg p-4 space-y-3">
            <p className="text-xs font-semibold text-muted-foreground">Import Settings</p>
            <div>
              <label htmlFor={`${uid}-sync-date`} className={LABEL_CLASS}>
                Sync Start Date
              </label>
              <input
                id={`${uid}-sync-date`}
                type="date"
                value={syncStartDate}
                onChange={(e) => setSyncStartDate(e.target.value)}
                className={INPUT_CLASS}
                data-testid="sync-start-date"
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-danger bg-danger/10 border border-danger/20 rounded-md px-3 py-2" data-testid="create-account-error">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={createMutation.isPending}
              className="px-4 py-2 text-sm font-medium bg-background text-foreground border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              data-testid="submit-create-account"
            >
              {createMutation.isPending ? "Creating..." : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
