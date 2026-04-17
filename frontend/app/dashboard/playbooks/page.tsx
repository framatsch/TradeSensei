/**
 * Playbooks page — list, create, edit, and delete playbook strategies.
 */

import { PageHeader } from "@/components/ui/PageHeader";
import { PlaybookList } from "@/components/playbooks/PlaybookList";

export const metadata = {
  title: "Playbooks — Trade Sensei",
};

export default function PlaybooksPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Playbooks"
        subtitle="Define and manage your trading strategies and setup types"
      />
      <PlaybookList />
    </div>
  );
}
