"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Grid3x3, LayoutDashboard, Library, Clock } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { useAppContext } from "@/hooks/useAppContext";
import { AppContext } from "@/stores/appContextStore";

export function BentoMenu() {
  const { activeContext, setActiveContext } = useAppContext();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const handleSelect = (ctx: AppContext, route: string) => {
    setActiveContext(ctx);
    setOpen(false);
    router.push(route);
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen} modal={false}>
      <Popover.Trigger asChild>
        <button
          className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Application Context"
        >
          <Grid3x3 className="w-5 h-5" />
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          className="z-50 w-64 p-2 bg-popover border border-border rounded-md shadow-md text-popover-foreground outline-none animate-in fade-in-80 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95"
          align="start"
          sideOffset={8}
        >
          <div className="flex flex-col gap-1">
            <button
              onClick={() => handleSelect("portfolio", "/dashboard")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
            >
              <LayoutDashboard className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Portfolio Workspace</span>
              {activeContext === "portfolio" && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </button>

            <button
              onClick={() => handleSelect("library", "/dashboard/library")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative"
            >
              <Library className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Global Library</span>
              {activeContext === "library" && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </button>

            <button
              onClick={() => handleSelect("checkin", "/dashboard/checkin")}
              className="flex items-center w-full p-2 text-sm rounded-md hover:bg-muted text-left transition-colors relative opacity-60"
            >
              <Clock className="w-4 h-4 mr-3 text-muted-foreground" />
              <span className="flex-1 font-medium">Market Check-in</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground ml-2">Coming Soon</span>
              {activeContext === "checkin" && (
                <span className="w-2 h-2 rounded-full bg-primary absolute right-3" />
              )}
            </button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
