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

import { ReactNode } from "react";
import { CheckinSidebar } from "@/components/checkin/CheckinSidebar";
import { ContextSetter } from "@/components/layout/ContextSetter";

export default function CheckinLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex w-full h-full">
      <div className="w-[220px] shrink-0 border-r border-border bg-sidebar">
        <CheckinSidebar />
      </div>
      <div className="flex-1 overflow-auto bg-background">
        {children}
      </div>
    </div>
  );
}
