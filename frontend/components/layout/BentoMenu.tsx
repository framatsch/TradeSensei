"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, Library, Clock, LineChart } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { useAppContext } from "@/hooks/useAppContext";
import { AppContext } from "@/stores/appContextStore";
import { LauncherIcon } from "@/components/icons/LauncherIcon";

export function BentoMenu() {
  const { activeContext, setActiveContext } = useAppContext();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const handleSelect = (ctx: AppContext) => {
    console.log("BentoMenu handleSelect called with", ctx);
    setActiveContext(ctx);
    setOpen(false);
  };

  const isPortfolio = activeContext === "portfolio" && !pathname.startsWith("/dashboard/trades");
  const isTradingLog = activeContext === "portfolio" && pathname.startsWith("/dashboard/trades");

  return (
    <Popover.Root open={open} onOpenChange={setOpen} modal={false}>
      <Popover.Trigger asChild>
        <button
          className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Application Context"
        >
          <LauncherIcon className="w-5 h-5" />
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          className="z-50 w-64 p-2 bg-popover border border-border rounded-md shadow-md text-popover-foreground outline-none animate-in fade-in-80 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95"
          align="start"
          sideOffset={8}
        >
          <div className="flex flex-col gap-1">
            <Link
              href="/dashboard"
              onClick={() => handleSelect("portfolio")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
              aria-current={isPortfolio ? "true" : undefined}
            >
              <LayoutDashboard className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Portfolio Workspace</span>
              {isPortfolio && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </Link>

            <Link
              href="/dashboard/trades"
              onClick={() => handleSelect("portfolio")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
              aria-current={isTradingLog ? "true" : undefined}
            >
              <LineChart className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Trading Log</span>
              {isTradingLog && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </Link>

            <Link
              href="/dashboard/library"
              onClick={() => handleSelect("library")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
              aria-current={activeContext === "library" ? "true" : undefined}
            >
              <Library className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Global Library</span>
              {activeContext === "library" && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </Link>

            <Link
              href="/dashboard/checkins"
              onClick={() => handleSelect("checkin")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
              aria-current={activeContext === "checkin" ? "true" : undefined}
            >
              <Clock className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Market Check-in</span>
              {activeContext === "checkin" && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </Link>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
