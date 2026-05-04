import { Suspense } from "react";
import { CheckinDateClient } from "./CheckinDateClient";
import { Spinner } from "@/components/ui/Spinner";

interface Props {
  params: Promise<{ date: string }>;
}

export async function generateMetadata({ params }: Props) {
  const { date } = await params;
  return {
    title: `Check-in ${date} — Trade Sensei`,
  };
}

export default async function CheckinDatePage({ params }: Props) {
  const { date } = await params;

  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64">
          <Spinner size="lg" />
        </div>
      }
    >
      <CheckinDateClient date={date} />
    </Suspense>
  );
}
