import { useQuery } from "@tanstack/react-query";
import { getModelBookEntriesApiV1ModelBookEntriesGet } from "@/lib/api/index";

export const MODEL_BOOK_ENTRIES_KEY = ["model-book", "entries"] as const;

export function useModelBookEntries(
  entityType?: "all" | "trade" | "checkin",
  fromDate?: string,
  toDate?: string,
  page: number = 1,
  limit: number = 30
) {
  return useQuery({
    queryKey: [...MODEL_BOOK_ENTRIES_KEY, { entityType, fromDate, toDate, page, limit }],
    queryFn: async () => {
      const response = await getModelBookEntriesApiV1ModelBookEntriesGet({
        query: {
          entity_type: entityType ?? "all",
          from_date: fromDate ?? null,
          to_date: toDate ?? null,
          page,
          per_page: limit,
        },
      });
      if (response.error || !response.data?.data) {
        throw response.error ?? new Error("Request failed: no data returned");
      }
      return response.data.data;
    },
  });
}
