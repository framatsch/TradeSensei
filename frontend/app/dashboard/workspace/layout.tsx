"use client";

import { WorkspaceFilterProvider } from "@/components/workspace/WorkspaceFilterContext";
import { WorkspaceFilterBar } from "@/components/workspace/WorkspaceFilterBar";
import { usePathname } from "next/navigation";
import { ContextSetter } from "@/components/layout/ContextSetter";

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isCalendar = pathname.endsWith("/calendar");

  return (
    <WorkspaceFilterProvider>
      <ContextSetter context="portfolio" />
      <div className="flex flex-col min-h-full">
        {!isCalendar && (
          <div className="p-6 pb-0">
            <WorkspaceFilterBar />
          </div>
        )}
        <div className="flex-1">
          {children}
        </div>
      </div>
    </WorkspaceFilterProvider>
  );
}