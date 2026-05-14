import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateTradeModelbookApiV1PortfoliosPortfolioIdTradesTradeIdModelbookPatch } from "@/lib/api/index";
import { useActivePortfolio } from "@/hooks/useActivePortfolio";

export function useTradeModelBook() {
  const queryClient = useQueryClient();
  const { activePortfolioId } = useActivePortfolio();

  return useMutation({
    mutationFn: async ({ tradeId, isModelbook }: { tradeId: string; isModelbook: boolean }) => {
      if (!activePortfolioId) throw new Error("No active portfolio");
      
      const response = await updateTradeModelbookApiV1PortfoliosPortfolioIdTradesTradeIdModelbookPatch({
        path: { portfolio_id: activePortfolioId, trade_id: tradeId },
        body: { is_modelbook: isModelbook },
      });
      return response.data?.data;
    },
    onSuccess: (data) => {
      if (data) {
        queryClient.invalidateQueries({ queryKey: ["trade", data.id] });
      }
      queryClient.invalidateQueries({ queryKey: ["trades"] });
      queryClient.invalidateQueries({ queryKey: ["model-book"] });
    },
  });
}
