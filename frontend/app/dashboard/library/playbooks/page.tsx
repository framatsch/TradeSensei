import { PageHeader } from "@/components/ui/PageHeader";
import { PlaybookList } from "@/components/playbooks/PlaybookList";
import { ContextSetter } from "@/components/layout/ContextSetter";

export const metadata = {
  title: "Playbooks — Trade Sensei",
};

export default function PlaybooksPage() {
  return (
    <div className="space-y-6">
      <ContextSetter context="library" />
      <PageHeader
        title="Playbooks"
        subtitle="Define and manage your trading strategies and setup types"
      />
      <PlaybookList />
    </div>
  );
}
