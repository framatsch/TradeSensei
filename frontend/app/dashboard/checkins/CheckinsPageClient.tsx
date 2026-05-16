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

import { useCheckinParams } from "@/hooks/useCheckinParams";
import { RegimePills } from "@/components/checkin/RegimePills";
import { TimelineView } from "@/components/checkin/TimelineView";
import { ModelBookView } from "@/components/checkin/ModelBookView";
import { GalleryView } from "@/components/checkin/GalleryView";
import Link from "next/link";
import { PlusCircle } from "lucide-react";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CheckinsPageClient() {
  const { view } = useCheckinParams();

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">
            Check-ins
          </h1>
          <Link 
            href={`/dashboard/checkins/${today()}`}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground hover:bg-primary/90 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            <PlusCircle className="w-4 h-4" />
            Today's Check-in
          </Link>
        </div>
        
        {/* Render RegimePills at the top of the main content area */}
        <RegimePills />

        {view === "gallery" ? (
          <GalleryView />
        ) : view === "modelbook" ? (
          <ModelBookView />
        ) : (
          <TimelineView />
        )}
      </div>
    </div>
  );
}
