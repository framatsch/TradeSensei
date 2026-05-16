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

/**
 * MetricHelpLink — A small (?) icon that opens the help page
 * at the relevant metric anchor in a popup window.
 */

"use client";

import { HelpCircle } from "lucide-react";

interface MetricHelpLinkProps {
  anchor: string;
}

const POPUP_FEATURES =
  "width=1120,height=760,resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no";

export function MetricHelpLink({ anchor }: MetricHelpLinkProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    window.open(`/help#${anchor}`, "tradesensei-help", POPUP_FEATURES);
  };

  return (
    <a
      href={`/help#${anchor}`}
      onClick={handleClick}
      aria-label="Help"
      className="text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded"
    >
      <HelpCircle size={12} strokeWidth={2} />
    </a>
  );
}
