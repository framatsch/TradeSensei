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

import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useCheckinParams } from "@/hooks/useCheckinParams";

export function RegimePills() {
  const { data: phases } = useGetTaxonomies("checkins");
  const { regime, setRegime } = useCheckinParams();

  const activePhases = phases ?? [];

  if (activePhases.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {activePhases.map((phase) => {
        const isActive = regime === phase.name;
        return (
          <button
            key={phase.id}
            onClick={() => setRegime(isActive ? null : phase.name)}
            className={`px-3 py-1 text-sm font-medium rounded-full border transition-colors ${
              isActive
                ? "bg-muted text-foreground"
                : "bg-transparent text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
            style={{
              borderColor: isActive ? phase.color_hex : `${phase.color_hex}40`,
            }}
          >
            {phase.name}
          </button>
        );
      })}
    </div>
  );
}
