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

import { Star } from "lucide-react";

interface StarButtonProps {
  isStarred: boolean;
  isLoading?: boolean;
  onClick: () => void;
  className?: string;
}

export function StarButton({ isStarred, isLoading, onClick, className = "" }: StarButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-zinc-100 hover:text-zinc-900 disabled:pointer-events-none disabled:opacity-50 dark:hover:bg-zinc-800 dark:hover:text-zinc-50 h-9 w-9 ${className}`}
      onClick={onClick}
      disabled={isLoading}
      aria-label={isStarred ? "Unstar" : "Star"}
    >
      <Star
        className={`h-5 w-5 ${isStarred ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
      />
    </button>
  );
}
