import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateCheckinModelbookApiV1CheckinsCheckinDateModelbookPatch } from "@/lib/api/index";

export function useCheckinModelBook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ date, isModelbook }: { date: string; isModelbook: boolean }) => {
      const response = await updateCheckinModelbookApiV1CheckinsCheckinDateModelbookPatch({
        path: { checkin_date: date },
        body: { is_modelbook: isModelbook },
      });
      if (response.error || !response.data?.data) {
        throw response.error ?? new Error("Request failed: no data returned");
      }
      return response.data.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["checkins"] });
      if (data) {
        queryClient.invalidateQueries({ queryKey: ["checkin", data.date] });
      }
      queryClient.invalidateQueries({ queryKey: ["model-book"] });
    },
  });
}
