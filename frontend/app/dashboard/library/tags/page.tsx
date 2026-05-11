import { PageHeader } from "@/components/ui/PageHeader";
import { TaxonomyManager } from "@/components/library/TaxonomyManager";

export const metadata = {
  title: "Tags — Trade Sensei",
};

export default function TagsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Tags (Taxonomies)"
        subtitle="Manage reusable metadata taxonomies for trades and check-ins"
      />
      <TaxonomyManager />
    </div>
  );
}
