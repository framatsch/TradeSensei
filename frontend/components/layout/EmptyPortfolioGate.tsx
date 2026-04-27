import Link from "next/link";
import { Briefcase } from "lucide-react";

export function EmptyPortfolioGate() {
  return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-var(--topbar-height,3.5rem))] px-4 bg-background">
      <div className="flex flex-col items-center text-center max-w-md bg-card p-8 rounded-2xl border border-border shadow-sm">
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-6">
          <Briefcase className="w-8 h-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          No portfolios yet
        </h2>
        <p className="text-muted-foreground mb-8 leading-relaxed">
          Create a portfolio to start journaling your trades, analyzing your performance, and building your strategies.
        </p>
        <Link
          href="/dashboard/settings?tab=portfolios"
          className="inline-flex items-center justify-center bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-3 rounded-md font-medium text-sm transition-colors w-full"
        >
          Create your first portfolio
        </Link>
      </div>
    </div>
  );
}
