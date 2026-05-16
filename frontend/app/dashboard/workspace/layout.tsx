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