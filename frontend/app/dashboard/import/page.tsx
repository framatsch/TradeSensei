/**
 * Import page — broker file upload form.
 */

import { PageHeader } from "@/components/ui/PageHeader";
import { ImportForm } from "@/components/imports/ImportForm";

export const metadata = {
  title: "Import — Trade Journal",
};

export default function ImportPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="Import Trades"
        subtitle="Upload a broker activity file to import your trades"
      />
      <ImportForm />
    </div>
  );
}
