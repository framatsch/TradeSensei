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
