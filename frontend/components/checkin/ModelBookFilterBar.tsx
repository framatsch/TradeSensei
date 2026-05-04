"use client";

interface Props {
  fromDate: string | null;
  setFromDate: (d: string | null) => void;
  toDate: string | null;
  setToDate: (d: string | null) => void;
  perPage: number;
  setPerPage: (p: number) => void;
}

export function ModelBookFilterBar({
  fromDate,
  setFromDate,
  toDate,
  setToDate,
  perPage,
  setPerPage,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground whitespace-nowrap">From</label>
        <input
          type="date"
          value={fromDate ?? ""}
          onChange={(e) => setFromDate(e.target.value || null)}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground whitespace-nowrap">To</label>
        <input
          type="date"
          value={toDate ?? ""}
          onChange={(e) => setToDate(e.target.value || null)}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        />
      </div>
      <div className="flex items-center gap-2 ml-auto">
        <label className="text-sm text-muted-foreground whitespace-nowrap">Items per page</label>
        <select
          value={perPage}
          onChange={(e) => setPerPage(Number(e.target.value))}
          className="text-sm border border-border rounded px-2 py-1 bg-background text-foreground"
        >
          <option value={12}>12</option>
          <option value={24}>24</option>
          <option value={48}>48</option>
        </select>
      </div>
    </div>
  );
}
