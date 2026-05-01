import { TradingLogSidebar } from "@/components/trading-log/TradingLogSidebar";

export default function TradesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full w-full">
      <div className="w-64 border-r border-border bg-sidebar flex-shrink-0">
        <TradingLogSidebar />
      </div>
      <div className="flex-1 overflow-auto bg-background p-6 pt-14">
        {children}
      </div>
    </div>
  );
}
