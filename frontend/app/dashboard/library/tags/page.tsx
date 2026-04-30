import { PageHeader } from "@/components/ui/PageHeader";
import { TagList } from "@/components/tags/TagList";
import { ContextSetter } from "@/components/layout/ContextSetter";

export const metadata = {
  title: "Tags — Trade Sensei",
};

export default function TagsPage() {
  return (
    <div className="space-y-6">
      <ContextSetter context="library" />
      <PageHeader
        title="Tags"
        subtitle="Organize trades with custom colored labels"
      />
      <TagList />
    </div>
  );
}
