/**
 * Tags page — create and manage trade tags with custom colors.
 */

import { PageHeader } from "@/components/ui/PageHeader";
import { TagList } from "@/components/tags/TagList";

export const metadata = {
  title: "Tags — Trade Journal",
};

export default function TagsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Tags"
        subtitle="Organize trades with custom colored labels"
      />
      <TagList />
    </div>
  );
}
