import { PageHeader } from "@/components/ui/PageHeader";
import { ContextSetter } from "@/components/layout/ContextSetter";
import { Clock } from "lucide-react";

export const metadata = {
  title: "Market Check-in — Trade Sensei",
};

export default function CheckinPage() {
  return (
    <div className="space-y-6">
      <ContextSetter context="checkin" />
      <PageHeader
        title="Market Check-in"
        subtitle="Chronological macro and psychological entries"
      />
      <div className="flex flex-col items-center justify-center py-24 px-4 bg-background">
        <div className="flex flex-col items-center text-center max-w-md bg-card p-8 rounded-2xl border border-border shadow-sm opacity-80">
          <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-6">
            <Clock className="w-8 h-8 text-muted-foreground" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Coming Soon
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Market Check-in will be available in a future update. Here you will be able to journal macro thoughts and psychological state over time.
          </p>
        </div>
      </div>
    </div>
  );
}
