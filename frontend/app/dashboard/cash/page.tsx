/**
 * Cash & Dividends page — server component metadata wrapper.
 */

import { Suspense } from "react";
import { CashPageClient } from "./CashPageClient";
import { Spinner } from "@/components/ui/Spinner";

export const metadata = {
  title: "Cash & Dividends — Trade Sensei",
};

export default function CashPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      }
    >
      <CashPageClient />
    </Suspense>
  );
}
