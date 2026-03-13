/**
 * Steuerbericht — annual tax summary page for German Anlage KAP reporting.
 *
 * Displays realised P&L in EUR grouped by §20 EStG categories:
 * - §20 Abs. 2 Nr. 1 EStG: Equity (stock) trades
 * - §20 Abs. 2 Nr. 3 EStG: Derivatives (options, futures, forex, crypto)
 */

"use client";

import { useState } from "react";
import { useTaxSummary } from "@/hooks/useTaxSummary";
import { PageHeader } from "@/components/ui/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import type { TaxCategoryBlock } from "@/lib/types";

const API_BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : "http://localhost:8000";

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 6 }, (_, i) => CURRENT_YEAR - i);

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
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4">
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

      <div className="pt-3 border-t border-slate-700 flex items-center justify-between">
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
          <p className="text-lg font-semibold text-slate-300">
            {block.trade_count}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatEur(value: string): string {
  const num = parseFloat(value);
  if (isNaN(num)) return "—";
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

function isEmpty(summary: { equities: TaxCategoryBlock; derivatives: TaxCategoryBlock }): boolean {
  return (
    summary.equities.trade_count === 0 &&
    summary.derivatives.trade_count === 0
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TaxPage() {
  const [year, setYear] = useState(CURRENT_YEAR);

  const { data: summary, isLoading, isError, error, refetch } = useTaxSummary(year);

  const csvUrl = `${API_BASE_URL}/api/v1/tax/annual-summary/csv?year=${year}`;

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
          className="px-3 py-2 bg-slate-700 border border-slate-600 text-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        <div className="flex flex-col items-center justify-center h-64 text-center bg-slate-800 border border-slate-700 rounded-xl px-8 py-12">
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
          <p className="text-slate-400 font-medium text-lg mb-1">
            Keine EUR-Daten für {year}
          </p>
          <p className="text-slate-500 text-sm max-w-sm">
            Es wurden keine abgeschlossenen Trades mit bekanntem EUR-Kurs für{" "}
            {year} gefunden. Trades werden beim Import mit dem offiziellen
            Bundesbank-Wechselkurs umgerechnet.
          </p>
        </div>
      )}

      {/* Summary cards */}
      {summary && !isEmpty(summary) && (
        <>
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

          {/* Total net */}
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">
                Gesamt-Netto {year} (§20 EStG)
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
    </div>
  );
}
