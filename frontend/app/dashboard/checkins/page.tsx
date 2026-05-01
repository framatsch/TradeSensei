import { Suspense } from "react";
import { CheckinsPageClient } from "./CheckinsPageClient";
import { Spinner } from "@/components/ui/Spinner";

export const metadata = {
  title: "Check-ins — Trade Sensei",
};

export default function CheckinsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      }
    >
      <CheckinsPageClient />
    </Suspense>
  );
}
