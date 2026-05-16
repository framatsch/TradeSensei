/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

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
