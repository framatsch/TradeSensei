"use client";

import Link from "next/link";
import { PanelLeftOpen, Home } from "lucide-react";
import { BentoMenu } from "./BentoMenu";
import { PortfolioSwitcher } from "./PortfolioSwitcher";
import { UserBadge } from "./UserBadge";
import { useAppContext } from "@/hooks/useAppContext";
import { useSettings } from "@/hooks/useSettings";

interface TopBarProps {
  onToggleSidebar: () => void;
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  const { activeContext } = useAppContext();
  const { data: settings } = useSettings();

  const homeRoute = (settings as any)?.home_route || "/dashboard";

  return (
    <header className="sticky top-0 h-[var(--topbar-height,3.5rem)] w-full border-b border-border bg-sidebar z-40 flex items-center justify-between px-4 lg:px-6">
      {/* Left section */}
      <div className="flex items-center gap-2 lg:gap-4 w-1/3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring lg:hidden"
          aria-label="Toggle Sidebar"
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>
        <button
          onClick={onToggleSidebar}
          className="hidden lg:flex p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Toggle Sidebar"
        >
          <PanelLeftOpen className="w-5 h-5" />
        </button>
        <div className="h-6 w-px bg-border/50 mx-1 hidden lg:block" />
        <BentoMenu />
        <Link
          href={homeRoute}
          className="hidden sm:flex p-2 rounded-md hover:bg-muted text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring ml-1"
          aria-label="Home"
        >
          <Home className="w-5 h-5" />
        </Link>
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
