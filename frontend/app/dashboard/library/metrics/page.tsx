import { PageHeader } from "@/components/ui/PageHeader";
import { AnnotationManager } from "@/components/library/AnnotationManager";

export const metadata = {
  title: "Metrics — Trade Sensei",
};

export default function MetricsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Metrics"
        subtitle="Manage reusable annotation definitions for trades and check-ins"
      />
      <AnnotationManager />
    </div>
  );
}