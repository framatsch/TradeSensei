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

import { useQuery } from '@tanstack/react-query';
import { listPortfoliosApiV1PortfoliosGet } from '@/lib/api/index';

export const usePortfolios = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const response = await listPortfoliosApiV1PortfoliosGet();
      if (response.error) throw response.error;
      return response.data?.data || [];
    },
    staleTime: 60000,
  });

  return {
    portfolios: data || [],
    isLoading,
    isError,
  };
};
