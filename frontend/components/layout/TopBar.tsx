"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftOpen, PanelLeftClose, Home } from "lucide-react";
import { BentoMenu } from "./BentoMenu";
import { PortfolioSwitcher } from "./PortfolioSwitcher";
import { UserBadge } from "./UserBadge";
import { useAppContext } from "@/hooks/useAppContext";
import { useSettings } from "@/hooks/useSettings";

interface TopBarProps {
  onToggleMobileSidebar: () => void;
  onToggleDesktopSidebar: () => void;
  isMobileSidebarOpen: boolean;
  isDesktopSidebarOpen: boolean;
}

export function TopBar({ onToggleMobileSidebar, onToggleDesktopSidebar, isMobileSidebarOpen, isDesktopSidebarOpen }: TopBarProps) {
  const { activeContext } = useAppContext();
  const { data: settings } = useSettings();
  const pathname = usePathname();

  const ALLOWED_HOME_ROUTES = ["/dashboard", "/dashboard/trades", "/dashboard/library", "/dashboard/checkins"] as const;
  type HomeRoute = typeof ALLOWED_HOME_ROUTES[number];
  const homeRoute: HomeRoute = ALLOWED_HOME_ROUTES.includes(settings?.home_route as HomeRoute)
    ? (settings!.home_route as HomeRoute)
    : "/dashboard";

  let contextLabel = "";
  if (activeContext === "portfolio") {
    contextLabel = pathname.startsWith("/dashboard/trades") ? "Trading Log" : "Portfolio Workspace";
  } else if (activeContext === "library") {
    contextLabel = "Global Library";
  } else if (activeContext === "checkin") {
    contextLabel = "Market Check-in";
  }

  return (
    <header className="sticky top-0 h-[var(--topbar-height,3.5rem)] w-full border-b border-border bg-sidebar z-40 flex items-center justify-between px-4 lg:px-6">
      {/* Left section */}
      <div className="flex items-center w-1/3">
        <div className="flex items-center gap-1">
          <button
            onClick={onToggleMobileSidebar}
            className="p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
            aria-label="Toggle Sidebar"
          >
            {isMobileSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
          </button>
          <button
            onClick={onToggleDesktopSidebar}
            className="hidden lg:flex p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Toggle Sidebar"
          >
            {isDesktopSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
          </button>
          
          <Link
            href={homeRoute}
            className="hidden sm:flex p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Home"
          >
            <Home className="w-5 h-5" />
          </Link>
          
          <BentoMenu />
        </div>

        <span className="text-sm font-semibold tracking-wide text-foreground whitespace-nowrap ml-6 hidden sm:block border-l border-border/50 pl-6">
          {contextLabel}
        </span>
      </div>

      {/* Center section */}
      <div className="flex items-center justify-center w-1/3">
        {activeContext === "portfolio" && <PortfolioSwitcher />}
      </div>

      {/* Right section */}
      <div className="flex items-center justify-end w-1/3">
        <UserBadge />
      </div>
    </header>
  );
}
