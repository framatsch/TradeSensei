"use client";

import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SETTINGS_KEY } from "@/hooks/useSettings";
import { FEATURE_FLAGS } from "@/lib/featureFlags";
import Link from "next/link";

export default function FeatureGatedNavItems({ onInject }: { onInject?: () => void }) {
  const qc = useQueryClient();
  const settings = qc.getQueryData(SETTINGS_KEY) as any | undefined;
  const features: Record<string, boolean> = settings?.features ?? {};

  const items: { href: string; label: string; icon: React.ReactNode }[] = [];
  if (features["cash_and_dividends"]) {
    items.push({ href: "/dashboard/cash", label: "Cash & Dividends", icon: null });
  }
  if (features["tax_report"]) {
    items.push({ href: "/dashboard/tax", label: "Steuerbericht", icon: null });
  }

  if (!items.length) return null;

  // Inform parent that items were injected (optional)
  if (onInject) onInject();

  return (
    <div className="space-y-0.5">
      {items.map((it) => (
        <Link key={it.href} href={it.href} className="flex items-center gap-3 px-4 py-2 text-sm font-normal rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60">
          <span className="shrink-0 opacity-50">{it.icon}</span>
          {it.label}
        </Link>
      ))}
    </div>
  );
}
