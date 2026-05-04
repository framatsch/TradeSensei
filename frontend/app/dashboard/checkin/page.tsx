"use client";

import { useState, useMemo } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { ContextSetter } from "@/components/layout/ContextSetter";
import { useCheckinEntries, useCheckinEntry, useCreateCheckin, useUpdateCheckin, useDeleteCheckin } from "@/hooks/useCheckins";
import { useMarketPhases } from "@/hooks/useCheckinDefinitions";
import { useCheckinFields } from "@/hooks/useCheckinDefinitions";
import type { DailyCheckinRead, DailyCheckinCreate, DailyCheckinUpdate } from "@/lib/api/types.gen";
import { Calendar, PlusCircle, Trash2, X, Link2, Loader2, Check, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ScreenshotUploader } from "@/components/checkin/ScreenshotUploader";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function fmtDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ─── Timeline ─────────────────────────────────────────────────────────────────

function TimelineEntry({
  date,
  isSelected,
  hasEntry,
  marketPhase,
  onClick,
}: {
  date: string;
  isSelected: boolean;
  hasEntry: boolean;
  marketPhase?: string | null;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center gap-2 ${
        isSelected
          ? "bg-primary/10 text-primary font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
      }`}
    >
      <span
        className={`w-2 h-2 rounded-full shrink-0 ${
          hasEntry
            ? "bg-emerald-400"
            : "bg-muted-foreground/30"
        }`}
      />
      <span className="flex-1 truncate">{fmtDate(date)}</span>
      {marketPhase && (
        <span className="text-[11px] text-muted-foreground truncate max-w-[80px]">
          {marketPhase}
        </span>
      )}
    </button>
  );
}

function TimelinePanel({
  entries,
  selectedDate,
  onSelect,
  dateRange,
  isLoading,
}: {
  entries: DailyCheckinRead[];
  selectedDate: string;
  onSelect: (d: string) => void;
  dateRange: string[];
  isLoading: boolean;
}) {
  const entryMap = useMemo(() => {
    const m = new Map<string, DailyCheckinRead>();
    for (const e of entries) m.set(e.date, e);
    return m;
  }, [entries]);

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
        <Calendar className="w-4 h-4 text-muted-foreground" />
        Timeline
      </h3>
      {isLoading ? (
        <div className="flex justify-center py-6">
          <Loader2 className="w-5 h-5 text-muted-foreground animate-spin" />
        </div>
      ) : (
        <div className="space-y-0.5 max-h-[500px] overflow-y-auto">
          {dateRange.map((d) => {
            const e = entryMap.get(d);
            return (
              <TimelineEntry
                key={d}
                date={d}
                isSelected={d === selectedDate}
                hasEntry={!!e}
                marketPhase={e?.market_phase}
                onClick={() => onSelect(d)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Form ─────────────────────────────────────────────────────────────────────

function CheckinForm({
  date,
  entry,
  marketPhases,
  customFields,
  onSave,
  onDelete,
  isSaving,
  isDeleting,
}: {
  date: string;
  entry: DailyCheckinRead | null | undefined;
  marketPhases: { name: string; label: string; color_hex: string; is_active: boolean }[];
  customFields: { field_name: string; field_type: "integer" | "boolean"; is_active: boolean }[];
  onSave: (data: DailyCheckinCreate | DailyCheckinUpdate) => void;
  onDelete: () => void;
  isSaving: boolean;
  isDeleting: boolean;
}) {
  const [marketPhase, setMarketPhase] = useState(entry?.market_phase ?? "");
  const [notes, setNotes] = useState(entry?.notes ?? "");
  const [newsLink, setNewsLink] = useState("");
  const [newsLinks, setNewsLinks] = useState<string[]>(entry?.news_links ?? []);
  const [screenshotUrls, setScreenshotUrls] = useState<string[]>(entry?.screenshot_urls ?? []);
  const [metrics, setMetrics] = useState<Record<string, number | boolean>>(entry?.custom_metrics ?? {});
  const [notesTab, setNotesTab] = useState<"write" | "preview">("write");

  const isNew = !entry;
  const activePhases = marketPhases.filter((p) => p.is_active);
  const activeFields = customFields.filter((f) => f.is_active);

  const addNewsLink = () => {
    const trimmed = newsLink.trim();
    if (trimmed && !newsLinks.includes(trimmed)) {
      setNewsLinks((prev) => [...prev, trimmed]);
      setNewsLink("");
    }
  };

  const removeNewsLink = (idx: number) => {
    setNewsLinks((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const showPhase = marketPhase || null;
    const showNotes = notes || null;

    if (isNew) {
      const payload: DailyCheckinCreate = {
        date,
        market_phase: showPhase,
        notes: showNotes,
        news_links: newsLinks.length > 0 ? newsLinks : undefined,
        screenshot_urls: screenshotUrls.length > 0 ? screenshotUrls : undefined,
        custom_metrics: Object.keys(metrics).length > 0 ? metrics : undefined,
      };
      onSave(payload);
    } else {
      const payload: DailyCheckinUpdate = {
        market_phase: showPhase,
        notes: showNotes,
        news_links: newsLinks,
        screenshot_urls: screenshotUrls,
        custom_metrics: metrics,
      };
      onSave(payload);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Market Phase */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Market Phase
        </label>
        <div className="flex flex-wrap gap-2">
          {activePhases.map((p) => {
            const isActive = marketPhase === p.name;
            return (
              <button
                key={p.name}
                type="button"
                onClick={() => setMarketPhase(isActive ? "" : p.name)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                style={{
                  backgroundColor: isActive ? p.color_hex + "20" : "transparent",
                  color: isActive ? p.color_hex : "var(--muted-foreground)",
                  borderColor: isActive ? p.color_hex + "40" : "var(--border)",
                  borderWidth: 1,
                }}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: isActive ? p.color_hex : "var(--muted-foreground)" }}
                />
                {p.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Notes */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-foreground">
            Notes
          </label>
          <div className="flex bg-muted/50 p-0.5 rounded-lg border border-border">
            <button
              type="button"
              onClick={() => setNotesTab("write")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                notesTab === "write"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Write
            </button>
            <button
              type="button"
              onClick={() => setNotesTab("preview")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                notesTab === "preview"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Preview
            </button>
          </div>
        </div>
        {notesTab === "write" ? (
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={6}
            placeholder="How did the market feel today? Any macro events? Psychological state?"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors resize-y"
          />
        ) : (
          <div className="w-full rounded-lg border border-border bg-muted/20 px-3 py-2 text-sm text-foreground min-h-[148px] prose prose-sm dark:prose-invert max-w-none">
            {notes.trim() ? (
              <ReactMarkdown>{notes}</ReactMarkdown>
            ) : (
              <span className="text-muted-foreground/50 italic">Nothing to preview.</span>
            )}
          </div>
        )}
      </div>

      {/* Screenshots */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          Screenshots
        </label>
        {screenshotUrls.length > 0 && (
          <div className="flex flex-wrap gap-3 mb-3">
            {screenshotUrls.map((url, i) => (
              <div key={i} className="relative group w-32 h-20 rounded-md overflow-hidden border border-border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt={`Screenshot ${i + 1}`}
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => setScreenshotUrls((prev) => prev.filter((_, idx) => idx !== i))}
                  className="absolute top-1 right-1 bg-background/80 hover:bg-destructive hover:text-destructive-foreground text-foreground p-1 rounded-sm opacity-0 group-hover:opacity-100 transition-all"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
        <ScreenshotUploader onUploaded={(url) => setScreenshotUrls((prev) => [...prev, url])} />
      </div>

      {/* News Links */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">
          News Links
        </label>
        {newsLinks.length > 0 && (
          <div className="space-y-1 mb-3">
            {newsLinks.map((link, i) => (
              <div
                key={i}
                className="flex items-center gap-2 bg-muted/40 rounded-md px-3 py-1.5 text-sm"
              >
                <Link2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <a
                  href={link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline truncate flex-1"
                >
                  {link}
                </a>
                <button
                  type="button"
                  onClick={() => removeNewsLink(i)}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="url"
            value={newsLink}
            onChange={(e) => setNewsLink(e.target.value)}
            placeholder="https://..."
            className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addNewsLink();
              }
            }}
          />
          <button
            type="button"
            onClick={addNewsLink}
            disabled={!newsLink.trim()}
            className="px-3 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <PlusCircle className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Custom Metrics */}
      {activeFields.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-foreground mb-3">
            Custom Metrics
          </label>
          <div className="space-y-3">
            {activeFields.map((field) => (
              <div key={field.field_name} className="flex items-center gap-3">
                <label className="text-sm text-muted-foreground min-w-[140px] capitalize">
                  {field.field_name.replace(/-/g, " ")}
                </label>
                {field.field_type === "boolean" ? (
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!metrics[field.field_name]}
                      onChange={(e) =>
                        setMetrics((prev) => ({
                          ...prev,
                          [field.field_name]: e.target.checked,
                        }))
                      }
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-0.5 after:start-[2px] after:bg-background after:border after:border-border after:rounded-full after:h-4 after:w-4 after:transition-all" />
                  </label>
                ) : (
                  <>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={
                        metrics[field.field_name] !== undefined
                          ? Number(metrics[field.field_name])
                          : 5
                      }
                      onChange={(e) => {
                        const v = e.target.value;
                        setMetrics((prev) => ({
                          ...prev,
                          [field.field_name]: parseInt(v, 10),
                        }));
                      }}
                      className="w-32 accent-primary"
                    />
                    <span className="text-sm w-4">
                      {metrics[field.field_name] !== undefined ? metrics[field.field_name] : 5}
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2 border-t border-border">
        <button
          type="submit"
          disabled={isSaving}
          className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          {isNew ? "Create Check-in" : "Save Changes"}
        </button>
        {!isNew && (
          <button
            type="button"
            onClick={onDelete}
            disabled={isDeleting}
            className="inline-flex items-center gap-2 border border-destructive/30 text-destructive hover:bg-destructive/10 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
            Delete
          </button>
        )}
      </div>
    </form>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CheckinPage() {
  const [selectedDate, setSelectedDate] = useState<string>(today());

  const { data: listData, isLoading: isListLoading } = useCheckinEntries();
  const { data: entryData, isLoading: isEntryLoading } = useCheckinEntry(selectedDate);
  const { data: phases, isLoading: isPhasesLoading } = useMarketPhases();
  const { data: fields, isLoading: isFieldsLoading } = useCheckinFields();
  const createMutation = useCreateCheckin();
  const updateMutation = useUpdateCheckin();
  const deleteMutation = useDeleteCheckin();

  const entries = listData?.items ?? [];
  const entry = entryData;

  const dateRange = useMemo(() => {
    const dates: string[] = [];
    const end = new Date();
    for (let i = 0; i < 60; i++) {
      const d = new Date(end);
      d.setDate(d.getDate() - i);
      dates.push(d.toISOString().slice(0, 10));
    }
    return dates;
  }, []);

  const handleSave = (data: DailyCheckinCreate | DailyCheckinUpdate) => {
    if (!entry) {
      createMutation.mutate(data as DailyCheckinCreate);
    } else {
      updateMutation.mutate({ date: selectedDate, payload: data as DailyCheckinUpdate });
    }
  };

  const handleDelete = () => {
    if (confirm("Delete this check-in? This cannot be undone.")) {
      deleteMutation.mutate(selectedDate);
    }
  };

  const isLoading = isListLoading || isEntryLoading || isPhasesLoading || isFieldsLoading;

  return (
    <div className="space-y-6">
      <ContextSetter context="checkin" />
      <PageHeader
        title="Market Check-in"
        subtitle="Daily macro and psychological journal"
      />

      <div className="flex gap-6 items-start flex-col lg:flex-row">
        {/* Form */}
        <div className="flex-1 min-w-0 w-full lg:max-w-2xl">
          <div className="bg-card border border-border rounded-xl p-6">
            {/* Date selector */}
            <div className="flex items-center gap-3 mb-6">
              <label className="text-sm font-medium text-foreground">
                Date
              </label>
              <input
                type="date"
                value={selectedDate}
                max={today()}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-colors"
              />
              {entry && (
                <span className="text-xs text-muted-foreground ml-auto">
                  Updated {new Date(entry.updated_at).toLocaleString()}
                </span>
              )}
            </div>

            {isLoading && !entry ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
              </div>
            ) : (
              <CheckinForm
                date={selectedDate}
                entry={entry}
                marketPhases={phases ?? []}
                customFields={fields ?? []}
                onSave={handleSave}
                onDelete={handleDelete}
                isSaving={createMutation.isPending || updateMutation.isPending}
                isDeleting={deleteMutation.isPending}
              />
            )}

            {/* Status messages */}
            {createMutation.isError && (
              <div className="mt-4 flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
                <AlertCircle className="w-4 h-4" />
                {createMutation.error?.message ?? "Failed to create check-in"}
              </div>
            )}
            {updateMutation.isError && (
              <div className="mt-4 flex items-center gap-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
                <AlertCircle className="w-4 h-4" />
                {updateMutation.error?.message ?? "Failed to update check-in"}
              </div>
            )}
          </div>
        </div>

        {/* Timeline */}
        <div className="w-full lg:w-64 shrink-0">
          <TimelinePanel
            entries={entries}
            selectedDate={selectedDate}
            onSelect={setSelectedDate}
            dateRange={dateRange}
            isLoading={isListLoading}
          />
        </div>
      </div>
    </div>
  );
}
