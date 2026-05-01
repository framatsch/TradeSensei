import { ReactNode } from "react";
import { CheckinSidebar } from "@/components/checkin/CheckinSidebar";

export default function CheckinLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex w-full h-full">
      <div className="w-[220px] shrink-0 border-r border-border bg-sidebar">
        <CheckinSidebar />
      </div>
      <div className="flex-1 overflow-auto bg-background">
        {children}
      </div>
    </div>
  );
}
