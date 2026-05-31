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

import type { TaxonomyResponse } from "@/lib/types";
import { DynamicIcon } from "@/components/ui/DynamicIcon";

interface Props {
  taxonomy: Pick<TaxonomyResponse, "id" | "name" | "color_hex" | "icon_identifier">;
}

export function TaxonomyBadge({ taxonomy }: Props) {
  const color = taxonomy.color_hex;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium"
      style={{
        backgroundColor: color ? `${color}1a` : "var(--muted)",
        borderColor: color ? `${color}66` : "var(--border)",
        color: color ?? "var(--foreground)",
      }}
      title={taxonomy.name}
    >
      {taxonomy.icon_identifier && (
        <DynamicIcon name={taxonomy.icon_identifier} className="w-3 h-3" />
      )}
      {taxonomy.name}
    </span>
  );
}
