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
  const { desktopSidebarOpen } = useSidebarStore();

  return (
    <CheckinFilterProvider>
      <div className="flex w-full h-full">
        <div
          className={`shrink-0 border-r border-border bg-sidebar transition-all duration-300 ease-in-out overflow-hidden ${
            desktopSidebarOpen ? "w-[220px]" : "w-0"
          }`}
        >
          <div className="w-[220px] h-full">
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
