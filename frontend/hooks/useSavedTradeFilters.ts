import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  SavedTradeFilterCreate,
  SavedTradeFilterRead,
  SavedTradeFilterUpdate,
} from "@/lib/types";
import {
  listSavedTradeFiltersApiV1SavedTradeFiltersGet,
  createSavedTradeFilterApiV1SavedTradeFiltersPost,
  updateSavedTradeFilterApiV1SavedTradeFiltersFilterIdPatch,
  deleteSavedTradeFilterApiV1SavedTradeFiltersFilterIdDelete,
} from "@/lib/api/index";

const QUERY_KEY = ["saved-trade-filters"];

export function useSavedTradeFilters() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const { data, error } = await listSavedTradeFiltersApiV1SavedTradeFiltersGet();
      if (error || !data) throw error;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as SavedTradeFilterRead[];
    },
  });
}

export function useCreateSavedTradeFilter() {
  const queryClient = useQueryClient();

  return useMutation<SavedTradeFilterRead, Error, SavedTradeFilterCreate>({
    mutationFn: async (payload) => {
      const { data, error } = await createSavedTradeFilterApiV1SavedTradeFiltersPost({
        body: payload as import("@/lib/api/types.gen").SavedTradeFilterCreate,
      });
      if (error || !data) throw error;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as SavedTradeFilterRead;
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
      const { data, error } = await updateSavedTradeFilterApiV1SavedTradeFiltersFilterIdPatch({
        path: { filter_id: id },
        body: payload as import("@/lib/api/types.gen").SavedTradeFilterUpdate,
      });
      if (error || !data) throw error;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (data as any).data as SavedTradeFilterRead;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

export function useDeleteSavedTradeFilter() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: async (filterId) => {
      const { error } = await deleteSavedTradeFilterApiV1SavedTradeFiltersFilterIdDelete({
        path: { filter_id: filterId },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
