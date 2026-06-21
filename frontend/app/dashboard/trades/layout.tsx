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

import { useSidebarStore } from "@/stores/sidebarStore";
import { TradingLogSidebar } from "@/components/trading-log/TradingLogSidebar";

export default function TradesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { desktopSidebarOpen, mobileSidebarOpen } = useSidebarStore();

  return (
    <div className="flex h-full w-full relative">
      <div
        className={`fixed lg:static top-[var(--topbar-height)] bottom-0 left-0 z-30 border-r border-border bg-sidebar flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden ${
          mobileSidebarOpen ? "translate-x-0 w-64" : "-translate-x-full w-64 lg:translate-x-0"
        } ${
          desktopSidebarOpen ? "lg:w-64" : "lg:w-0 lg:border-r-0"
        }`}
      >
        <div className="w-64 h-full">
          <TradingLogSidebar />
        </div>
      </div>
      <div className="flex-1 overflow-auto bg-background p-4 sm:p-6">
        {children}
      </div>
    </div>
  );
}
