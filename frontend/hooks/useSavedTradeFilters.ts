import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import apiClient from "@/lib/api";
import type {
  SavedTradeFilterCreate,
  SavedTradeFilterRead,
  SavedTradeFilterUpdate,
  ResponseEnvelope,
} from "@/lib/types";

const QUERY_KEY = ["saved-trade-filters"];

export function useSavedTradeFilters() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get<ResponseEnvelope<SavedTradeFilterRead[]>>(
        "/api/v1/saved-trade-filters"
      );
      return response.data.data;
    },
  });
}

export function useCreateSavedTradeFilter() {
  const queryClient = useQueryClient();

  return useMutation<SavedTradeFilterRead, Error, SavedTradeFilterCreate>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<ResponseEnvelope<SavedTradeFilterRead>>(
        "/api/v1/saved-trade-filters",
        payload
      );
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useUpdateSavedTradeFilter(id: string) {
  const queryClient = useQueryClient();

  return useMutation<SavedTradeFilterRead, Error, SavedTradeFilterUpdate>({
    mutationFn: async (payload) => {
      const response = await apiClient.patch<ResponseEnvelope<SavedTradeFilterRead>>(
        `/api/v1/saved-trade-filters/${id}`,
        payload
      );
      return response.data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useDeleteSavedTradeFilter() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/saved-trade-filters/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
