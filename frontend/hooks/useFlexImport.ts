/**
 * React Query mutation hook for IBKR Flex Query import.
 */

"use client";

import { useMutation } from "@tanstack/react-query";
import apiClient from "@/lib/api";
import type { ImportResult, ResponseEnvelope } from "@/lib/types";

interface FlexImportPayload {
  query_id: string;
  account_id?: string | null;
  from_date?: string | null;
}

export function useFlexImport() {
  return useMutation<ImportResult, Error, FlexImportPayload>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<ResponseEnvelope<ImportResult>>(
        "/api/v1/imports/flex",
        payload
      );
      return res.data.data;
    },
  });
}
