"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  LayoutDashboard,
  CalendarDays,
  LineChart,
  BarChart2 as BarChart3,
  Brain as BrainCircuit,
  Clock,
} from "lucide-react";

const NAV_CLASS = "flex items-center gap-3 px-3 py-2 text-sm transition-colors";
const ACTIVE_CLASS = "text-primary bg-primary/10 font-medium rounded-lg";
const INACTIVE_CLASS = "text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-lg";
const SECTION_HEADING_CLASS = "px-4 pt-1 pb-2 text-[11px] font-semibold tracking-[0.05em] uppercase text-slate-500 select-none mt-8 first:mt-0";

interface NavLinkProps {
  href: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
}

function NavLink({ href, icon, label, isActive }: NavLinkProps) {
  return (
    <Link
      href={href}
      className={`${NAV_CLASS} ${isActive ? `${ACTIVE_CLASS} nav-active` : INACTIVE_CLASS}`}
    >
      <span className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
        {icon}
      </span>
      <span className="truncate">{label}</span>
    </Link>
  );
}

export function WorkspaceSidebarNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Helper to preserve current filter state when navigating between tabs
  const buildHref = (basePath: string) => {
    const query = searchParams.toString();
    return query ? `${basePath}?${query}` : basePath;
  };

  return (
    <nav className="flex flex-col pb-8">
      <div className={SECTION_HEADING_CLASS}>Dashboard</div>
      <div className="space-y-0.5 px-2">
        <NavLink
          href="/dashboard"
          icon={<LayoutDashboard />}
          label="Home"
          isActive={pathname === "/dashboard"}
        />
        <NavLink
          href={buildHref("/dashboard/workspace/calendar")}
          icon={<CalendarDays />}
          label="Calendar"
          isActive={pathname === "/dashboard/workspace/calendar"}
        />
      </div>

      <div className={SECTION_HEADING_CLASS}>Workspace</div>
      <div className="space-y-0.5 px-2">
        <NavLink
          href={buildHref("/dashboard/workspace/overview")}
          icon={<BarChart3 />}
          label="Overview"
          isActive={pathname === "/dashboard/workspace/overview"}
        />
        <NavLink
          href={buildHref("/dashboard/workspace/reporting")}
          icon={<LineChart />}
          label="Reporting"
          isActive={pathname === "/dashboard/workspace/reporting"}
        />
        <NavLink
          href={buildHref("/dashboard/workspace/performance/time")}
          icon={<Clock />}
          label="Time"
          isActive={pathname === "/dashboard/workspace/performance/time"}
        />
        <NavLink
          href={buildHref("/dashboard/workspace/performance/strategy")}
          icon={<BarChart3 />}
          label="Strategy"
          isActive={pathname === "/dashboard/workspace/performance/strategy"}
        />
        <NavLink
          href={buildHref("/dashboard/workspace/performance/behavior")}
          icon={<BrainCircuit />}
          label="Behavior"
          isActive={pathname === "/dashboard/workspace/performance/behavior"}
        />
      </div>
    </nav>
  );
}
