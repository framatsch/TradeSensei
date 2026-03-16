/**
 * Trades list page — server wrapper for metadata + client logic.
 */

import { Suspense } from "react";
import { TradesPageClient } from "./TradesPageClient";
import { Spinner } from "@/components/ui/Spinner";

export const metadata = {
  title: "Trades — Trade Journal",
};

export default function TradesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      }
    >
      <TradesPageClient />
    </Suspense>
  );
}
