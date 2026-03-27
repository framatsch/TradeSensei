"use client";

import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { usePathname } from "next/navigation";
import { SETTINGS_KEY } from "@/hooks/useSettings";
import Link from "next/link";

export default function FeatureGatedNavItems({ onInject }: { onInject?: () => void }) {
  const qc = useQueryClient();
  const settings = qc.getQueryData(SETTINGS_KEY) as any | undefined;
  const features: Record<string, boolean> = settings?.features ?? {};

  const pathname = usePathname();

  const items: { href: string; label: string; icon: React.ReactNode }[] = [];
  if (features["cash_and_dividends"]) {
    items.push({
      href: "/dashboard/cash",
      label: "Cash & Dividends",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
          <line x1="12" y1="1" x2="12" y2="23" />
          <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
      ),
    });
  }
  if (features["tax_report"]) {
    items.push({
      href: "/dashboard/tax",
      label: "Steuerbericht",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-[18px] h-[18px]">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    });
  }

  if (!items.length) return null;

  // Inform parent that items were injected (optional)
  if (onInject) onInject();

  return (
    <div className="space-y-0.5">
      {items.map((it) => {
        const isActive = pathname === it.href || pathname?.startsWith(it.href);
        return (
          <Link
            key={it.href}
            href={it.href}
            className={`flex items-center gap-3 px-4 py-2 text-sm font-normal transition-all duration-150 ${
              isActive ? "nav-active" : "rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60"
            }`}
          >
            <span className={`shrink-0 ${isActive ? "opacity-100" : "opacity-50"}`}>{it.icon}</span>
            {it.label}
          </Link>
        );
      })}
    </div>
  );
}
