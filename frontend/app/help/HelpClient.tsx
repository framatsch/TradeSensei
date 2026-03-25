"use client";

/**
 * HelpClient — interactive shell for the help page.
 * - Sticky TOC on the left (highlights the active section while scrolling)
 * - Back-to-top button that appears after scrolling 200 px
 */

import { useEffect, useRef, useState } from "react";
import { ChevronUp } from "lucide-react";
import type { Section, MetricEntry } from "./page";

// ─── MetricCard ───────────────────────────────────────────────────────────────

function MetricCard({ entry }: { entry: MetricEntry }) {
  return (
    <section
      id={entry.id}
      className="scroll-mt-6 rounded-xl border border-border bg-card p-6 flex flex-col gap-3"
    >
      <h3 className="text-base font-semibold text-foreground">{entry.label}</h3>
      <p className="text-sm font-medium text-muted-foreground">{entry.summary}</p>
      <p className="text-sm text-foreground/80 leading-relaxed">{entry.detail}</p>

      {entry.formula && (
        <div className="mt-1 rounded-md bg-muted px-4 py-2 font-mono text-xs text-foreground/70">
          {entry.formula}
        </div>
      )}

      {(entry.good || entry.bad) && (
        <div className="mt-1 flex flex-col gap-1.5 text-xs">
          {entry.good && (
            <p className="flex gap-2">
              <span className="text-emerald-500 font-bold shrink-0">Good:</span>
              <span className="text-foreground/70">{entry.good}</span>
            </p>
          )}
          {entry.bad && (
            <p className="flex gap-2">
              <span className="text-rose-500 font-bold shrink-0">Watch out:</span>
              <span className="text-foreground/70">{entry.bad}</span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// ─── HelpClient ───────────────────────────────────────────────────────────────

interface Props {
  sections: Section[];
}

export function HelpClient({ sections }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState<string>("");
  const [showTop, setShowTop] = useState(false);

  // Track which metric is currently in view
  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const allIds = sections.flatMap((s) => s.entries.map((e) => e.id));

    const handleScroll = () => {
      setShowTop(container.scrollTop > 200);

      // Find the first entry whose top is still within the upper half of the viewport
      for (const id of [...allIds].reverse()) {
        const el = container.querySelector(`#${id}`);
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        if (rect.top - containerRect.top < containerRect.height * 0.5) {
          setActiveId(id);
          return;
        }
      }
      setActiveId(allIds[0] ?? "");
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => container.removeEventListener("scroll", handleScroll);
  }, [sections]);

  const scrollToTop = () => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  const scrollToId = (id: string) => {
    const el = scrollRef.current?.querySelector(`#${id}`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* ── Sticky TOC ─────────────────────────────────────── */}
      <nav className="w-48 shrink-0 flex flex-col border-r border-border overflow-y-auto py-5 px-3 gap-0">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-2 mb-3">
          Contents
        </p>

        {sections.map((section) => (
          <div key={section.heading} className="mb-3">
            <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground/50 px-2 mb-1">
              {section.heading}
            </p>
            {section.entries.map((entry) => {
              const isActive = activeId === entry.id;
              return (
                <button
                  key={entry.id}
                  onClick={() => scrollToId(entry.id)}
                  className={`w-full text-left px-2 py-1 rounded text-xs transition-colors ${
                    isActive
                      ? "bg-muted text-foreground font-medium"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  {entry.label}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* ── Scrollable content ─────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto relative">
        <div className="max-w-xl mx-auto py-8 px-5 flex flex-col gap-6">
          {/* Header */}
          <div className="flex flex-col gap-1">
            <h1 className="text-xl font-bold text-foreground">Metric Reference</h1>
            <p className="text-sm text-muted-foreground">
              Explanations for every metric and chart in your trading journal.
            </p>
          </div>

          {/* Sections */}
          {sections.map((section) => (
            <div key={section.heading} className="flex flex-col gap-4">
              <h2 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground px-1">
                {section.heading}
              </h2>
              {section.entries.map((entry) => (
                <MetricCard key={entry.id} entry={entry} />
              ))}
            </div>
          ))}

          {/* bottom padding so last card isn't flush against the edge */}
          <div className="h-8" />
        </div>

        {/* ── Back to top ──────────────────────────────────── */}
        {showTop && (
          <button
            onClick={scrollToTop}
            aria-label="Back to top"
            className="fixed bottom-5 right-5 z-50 flex items-center justify-center w-9 h-9 rounded-full bg-muted border border-border text-muted-foreground hover:text-foreground hover:bg-muted/80 shadow-md transition-colors"
          >
            <ChevronUp size={18} />
          </button>
        )}
      </div>
    </div>
  );
}
