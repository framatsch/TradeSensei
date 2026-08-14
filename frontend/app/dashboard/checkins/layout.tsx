/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

"use client";

import { ReactNode } from "react";
import { CheckinSidebar } from "@/components/checkin/CheckinSidebar";
import { CheckinFilterProvider } from "@/components/checkin/CheckinFilterContext";
import { useSidebarStore } from "@/stores/sidebarStore";

export default function CheckinLayout({ children }: { children: ReactNode }) {
  const { desktopSidebarOpen, mobileSidebarOpen, setMobileOpen } = useSidebarStore();

  return (
    <CheckinFilterProvider>
      <div className="flex w-full h-full relative">
        {mobileSidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/60 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
        <div
          className={`fixed lg:static top-[var(--topbar-height)] bottom-0 left-0 z-30 shrink-0 border-r border-border bg-sidebar transition-all duration-300 ease-in-out overflow-hidden ${
            mobileSidebarOpen ? "translate-x-0 w-64" : "-translate-x-full w-64 lg:translate-x-0"
          } ${
            desktopSidebarOpen ? "lg:w-64" : "lg:w-0 lg:border-r-0"
          }`}
        >
          <div className="w-64 h-full">
            <CheckinSidebar />
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-background">
          {children}
        </div>
      </div>
    </CheckinFilterProvider>
  );
}
