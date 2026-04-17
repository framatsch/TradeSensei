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
