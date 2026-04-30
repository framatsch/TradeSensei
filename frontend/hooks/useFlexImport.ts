/**
 * React Query mutation hook for IBKR Flex Query import.
 */

"use client";

import { useMutation } from "@tanstack/react-query";
import { client } from "@/lib/api/client.gen";
import type { ImportResult } from "@/lib/types";

interface FlexImportPayload {
  query_id: string;
  account_id?: string | null;
  from_date?: string | null;
}

export function useFlexImport() {
  return useMutation<ImportResult, Error, FlexImportPayload>({
    mutationFn: async (payload) => {
      const response = await client.post({
        url: "/api/v1/imports/flex",
        body: payload,
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const envelope = response as any;
      if (!envelope.data) throw new Error("Flex import failed");
      return (envelope.data.data ?? envelope.data) as ImportResult;
    },
  });
}
