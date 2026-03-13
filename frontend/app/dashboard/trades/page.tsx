/**
 * Trades list page with paginated TradeTable.
 */

import { PageHeader } from "@/components/ui/PageHeader";
import { TradeTable } from "@/components/trades/TradeTable";

export const metadata = {
  title: "Trades — Trade Journal",
};

export default function TradesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Trades"
        subtitle="All recorded trading positions"
      />
      <TradeTable />
    </div>
  );
}
