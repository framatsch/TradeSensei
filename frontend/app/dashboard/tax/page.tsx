/**
 * Steuerbericht — annual tax summary page for German Anlage KAP reporting.
 *
 * Displays realised P&L in EUR grouped by §20 EStG categories:
 * - §20 Abs. 2 Nr. 1 EStG: Equity (stock) trades
 * - §20 Abs. 2 Nr. 3 EStG: Derivatives (options, futures, forex, crypto)
 *
 * Also displays dividend, withholding-tax and interest income from
 * imported cash transactions (§20 Abs. 1 EStG).
 */

"use client";

import { useState } from "react";
import { useTaxSummary } from "@/hooks/useTaxSummary";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import type { TaxCategoryBlock, TaxAnnualSummary, AccountTaxSummary } from "@/lib/types";

// CSV download goes through the Next.js proxy in production; in dev it hits
// the backend directly via NEXT_PUBLIC_API_URL.
const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "/api/proxy"
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 6 }, (_, i) => CURRENT_YEAR - i);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatEur(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "—";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

function isEmpty(summary: TaxAnnualSummary): boolean {
  return (
    summary.equities.trade_count === 0 &&
    summary.derivatives.trade_count === 0 &&
    parseFloat(summary.dividends_eur ?? "0") === 0 &&
    parseFloat(summary.withholding_tax_eur ?? "0") === 0 &&
    parseFloat(summary.interest_eur ?? "0") === 0
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface CategoryCardProps {
  title: string;
  paragraph: string;
  block: TaxCategoryBlock;
  colorClass: string;
}

function CategoryCard({ title, paragraph, block, colorClass }: CategoryCardProps) {
  const net = parseFloat(block.net_eur);
  const netPositive = net >= 0;

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 space-y-4">
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">
          {paragraph}
        </p>
        <h3 className={`text-lg font-semibold mt-0.5 ${colorClass}`}>{title}</h3>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-slate-500 mb-1">Gewinne</p>
          <p className="text-xl font-bold text-green-400">
            {formatEur(block.gains_eur)}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500 mb-1">Verluste</p>
          <p className="text-xl font-bold text-red-400">
            {formatEur(block.losses_eur)}
          </p>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500 mb-1">Netto</p>
          <p
            className={`text-2xl font-bold ${
              netPositive ? "text-green-400" : "text-red-400"
            }`}
          >
            {formatEur(block.net_eur)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 mb-1">Trades</p>
          <p className="text-lg font-semibold text-slate-700 dark:text-slate-300">
            {block.trade_count}
          </p>
        </div>
      </div>
    </div>
  );
}

interface CashFlowCardProps {
  label: string;
  value: string;
  colorClass?: string;
  subLabel?: string;
}

function CashFlowCard({ label, value, colorClass = "text-slate-900 dark:text-slate-100", subLabel }: CashFlowCardProps) {
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 flex flex-col gap-1">
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        {label}
      </p>
      {subLabel && (
        <p className="text-xs text-slate-400 dark:text-slate-500 -mt-0.5">{subLabel}</p>
      )}
      <p className={`text-xl font-bold mt-1 ${colorClass}`}>{value}</p>
    </div>
  );
}

// ─── Account breakdown row ────────────────────────────────────────────────────

function AccountBreakdown({ acc }: { acc: AccountTaxSummary }) {
  const dividends = parseFloat(acc.dividends_eur ?? "0");
  const withholding = parseFloat(acc.withholding_tax_eur ?? "0");
  const interest = parseFloat(acc.interest_eur ?? "0");
  const hasCashData = dividends !== 0 || withholding !== 0 || interest !== 0;

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-medium text-slate-800 dark:text-slate-200">
          {acc.account_name || "Unbekanntes Konto"}
        </h3>
        <div className="text-right">
          <p className="text-sm text-slate-500">Konto-Netto (Trades)</p>
          <p className={`text-xl font-bold ${
            parseFloat(acc.total_net_eur) >= 0 ? "text-green-400" : "text-red-400"
          }`}>
            {formatEur(acc.total_net_eur)}
          </p>
        </div>
      </div>

      {/* Trade P&L breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-400 mb-3">Aktien (§20 Abs. 2 Nr. 1 EStG)</h4>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div>
              <p className="text-xs text-slate-500">Gewinne</p>
              <p className="text-sm font-semibold text-green-400">{formatEur(acc.equities.gains_eur)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Verluste</p>
              <p className="text-sm font-semibold text-red-400">{formatEur(acc.equities.losses_eur)}</p>
            </div>
          </div>
          <div className="flex justify-between items-end mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
            <div>
              <p className="text-xs text-slate-500">Netto</p>
              <p className={`text-sm font-bold ${parseFloat(acc.equities.net_eur) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatEur(acc.equities.net_eur)}
              </p>
            </div>
            <p className="text-xs text-slate-500">{acc.equities.trade_count} Trades</p>
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-purple-400 mb-3">Derivate (§20 Abs. 2 Nr. 3 EStG)</h4>
          <div className="grid grid-cols-2 gap-2 mb-2">
            <div>
              <p className="text-xs text-slate-500">Gewinne</p>
              <p className="text-sm font-semibold text-green-400">{formatEur(acc.derivatives.gains_eur)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Verluste</p>
              <p className="text-sm font-semibold text-red-400">{formatEur(acc.derivatives.losses_eur)}</p>
            </div>
          </div>
          <div className="flex justify-between items-end mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
            <div>
              <p className="text-xs text-slate-500">Netto</p>
              <p className={`text-sm font-bold ${parseFloat(acc.derivatives.net_eur) >= 0 ? "text-green-400" : "text-red-400"}`}>
                {formatEur(acc.derivatives.net_eur)}
              </p>
            </div>
            <p className="text-xs text-slate-500">{acc.derivatives.trade_count} Trades</p>
          </div>
        </div>
      </div>

      {/* Cash flow breakdown */}
      {hasCashData && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
          <h4 className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-3">
            Kapitalerträge (§20 Abs. 1 EStG)
          </h4>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Dividenden</p>
              <p className={`text-sm font-bold ${dividends >= 0 ? "text-green-500" : "text-red-400"}`}>
                {formatEur(acc.dividends_eur)}
              </p>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Quellensteuer</p>
              <p className={`text-sm font-bold ${withholding >= 0 ? "text-green-500" : "text-red-400"}`}>
                {formatEur(acc.withholding_tax_eur)}
              </p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Zinsen</p>
              <p className={`text-sm font-bold ${interest >= 0 ? "text-green-500" : "text-red-400"}`}>
                {formatEur(acc.interest_eur)}
              </p>
            </div>
          </div>
        </div>
      )}

      {acc.trades_missing_eur > 0 && (
        <p className="text-xs text-amber-500 mt-4 text-right">
          {acc.trades_missing_eur} Trade{acc.trades_missing_eur !== 1 ? "s" : ""} ohne EUR-Kurs
        </p>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TaxPage() {
  const [year, setYear] = useState(CURRENT_YEAR);

  const { data: summary, isLoading, isError, error, refetch } = useTaxSummary(year);

  const csvUrl = `${API_BASE_URL}/v1/tax/annual-summary/csv?year=${year}`;

  const handleCsvDownload = () => {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;

    if (!token) return;

    // Fetch with auth header and trigger a download via blob URL.
    fetch(csvUrl, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `steuer_${year}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      });
  };

  const dividends = summary ? parseFloat(summary.dividends_eur ?? "0") : 0;
  const withholding = summary ? parseFloat(summary.withholding_tax_eur ?? "0") : 0;
  const interest = summary ? parseFloat(summary.interest_eur ?? "0") : 0;
  const hasCashData = dividends !== 0 || withholding !== 0 || interest !== 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Steuerbericht"
        subtitle="Jahresübersicht für die Anlage KAP (§20 EStG)"
      >
        {/* Year selector */}
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-800 dark:text-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Steuerjahr auswählen"
        >
          {YEAR_OPTIONS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>

        {/* CSV download */}
        <button
          onClick={handleCsvDownload}
          title={`Anlage KAP CSV für ${year} herunterladen`}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="w-4 h-4"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          CSV herunterladen
        </button>
      </PageHeader>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <p className="text-red-400 font-medium mb-2">
            Steuerdaten konnten nicht geladen werden.
          </p>
          <p className="text-slate-500 text-sm mb-4">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm transition-colors"
          >
            Nochmals versuchen
          </button>
        </div>
      )}

      {/* Empty state */}
      {summary && isEmpty(summary) && (
        <div className="flex flex-col items-center justify-center h-64 text-center bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-8 py-12">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="w-12 h-12 text-slate-600 mb-4"
          >
            <path d="M9 14l6-6m-5.5.5h.01m4.99 5h.01" strokeLinecap="round" />
            <path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
          </svg>
          <p className="text-slate-600 dark:text-slate-400 font-medium text-lg mb-1">
            Keine EUR-Daten für {year}
          </p>
          <p className="text-slate-500 text-sm max-w-sm">
            Es wurden keine abgeschlossenen Trades oder Kapitalerträge mit bekanntem
            EUR-Kurs für {year} gefunden. Trades werden beim Import mit dem offiziellen
            Bundesbank-Wechselkurs umgerechnet.
          </p>
        </div>
      )}

      {/* Summary content */}
      {summary && !isEmpty(summary) && (
        <>
          {/* ── Section 1: Trading P&L (§20 Abs. 2) ─────────────────────────── */}
          {(summary.equities.trade_count > 0 || summary.derivatives.trade_count > 0) && (
            <>
              <div>
                <h2 className="text-base font-semibold text-slate-700 dark:text-slate-300 mb-3 uppercase tracking-wide text-xs">
                  §20 Abs. 2 EStG — Veräußerungsgewinne
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <CategoryCard
                    title="Aktien"
                    paragraph="§20 Abs. 2 Nr. 1 EStG"
                    block={summary.equities}
                    colorClass="text-blue-400"
                  />
                  <CategoryCard
                    title="Derivate"
                    paragraph="§20 Abs. 2 Nr. 3 EStG"
                    block={summary.derivatives}
                    colorClass="text-purple-400"
                  />
                </div>
              </div>

              {/* Total net trading P&L */}
              <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Gesamt-Netto Trades {year} (§20 Abs. 2 EStG)
                  </p>
                  <p
                    className={`text-3xl font-bold mt-1 ${
                      parseFloat(summary.total_net_eur) >= 0
                        ? "text-green-400"
                        : "text-red-400"
                    }`}
                  >
                    {formatEur(summary.total_net_eur)}
                  </p>
                </div>

                {summary.trades_missing_eur > 0 && (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-right">
                    <p className="text-amber-400 text-sm font-medium">
                      {summary.trades_missing_eur} Trade
                      {summary.trades_missing_eur !== 1 ? "s" : ""} ohne EUR-Kurs
                    </p>
                    <p className="text-amber-400/70 text-xs mt-0.5">
                      Kurs beim Import nicht verfügbar
                    </p>
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Section 2: Kapitalerträge (§20 Abs. 1) ───────────────────────── */}
          {hasCashData && (
            <div>
              <h2 className="text-base font-semibold text-slate-700 dark:text-slate-300 mb-3 uppercase tracking-wide text-xs">
                §20 Abs. 1 EStG — Kapitalerträge
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <CashFlowCard
                  label="Dividenden"
                  subLabel="§20 Abs. 1 Nr. 1 EStG"
                  value={formatEur(summary.dividends_eur)}
                  colorClass={dividends >= 0 ? "text-green-400" : "text-red-400"}
                />
                <CashFlowCard
                  label="Quellensteuer"
                  subLabel="Anrechenbare ausländische Steuer"
                  value={formatEur(summary.withholding_tax_eur)}
                  colorClass={withholding >= 0 ? "text-green-400" : "text-red-400"}
                />
                <CashFlowCard
                  label="Zinsen"
                  subLabel="§20 Abs. 1 Nr. 7 EStG"
                  value={formatEur(summary.interest_eur)}
                  colorClass={interest >= 0 ? "text-green-400" : "text-red-400"}
                />
              </div>
              {/* Net dividends after withholding */}
              <div className="mt-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Netto-Dividenden nach Quellensteuer {year}
                  </p>
                  <p
                    className={`text-2xl font-bold mt-1 ${
                      dividends + withholding >= 0 ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {formatEur(String(dividends + withholding))}
                  </p>
                </div>
                <p className="text-xs text-slate-500 max-w-xs text-right">
                  Quellensteuer auf US-Dividenden ist bis zu 15% auf die deutsche
                  Abgeltungsteuer anrechenbar (DBA USA).
                </p>
              </div>
            </div>
          )}

          {/* ── Breakdown by Account ──────────────────────────────────────────── */}
          {summary.accounts && summary.accounts.length > 0 && (
            <div className="mt-4">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-slate-200 mb-4">
                Aufschlüsselung nach Konto
              </h2>
              <div className="space-y-6">
                {summary.accounts.map((acc) => (
                  <AccountBreakdown key={acc.account_id || "unknown"} acc={acc} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
