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

import { icons } from "lucide-react";
import type { LucideProps } from "lucide-react";

interface DynamicIconProps extends Omit<LucideProps, "ref" | "name"> {
  name?: string | null;
  fallback?: keyof typeof icons;
}

export function DynamicIcon({ name, fallback = "Tag", ...props }: DynamicIconProps) {
  let IconComponent = icons[fallback];

  if (name) {
    // Convert name (e.g. "alert-circle" or "alertCircle") to Component name (e.g. "AlertCircle")
    // Note: lucide-react exports icons in PascalCase
    const formattedName = name
      .replace(/^lucide:/, "") // Sometimes prefixes are added
      .split("-")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join("");

    if (formattedName in icons) {
      IconComponent = icons[formattedName as keyof typeof icons];
    }
  }

  if (!IconComponent) {
    return null;
  }

  return <IconComponent {...props} />;
}
