import { useQuery } from '@tanstack/react-query';
import { listPortfoliosApiV1PortfoliosGet, PortfolioRead } from '@/lib/api/index';

export const usePortfolios = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const response = await listPortfoliosApiV1PortfoliosGet();
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
