import { useEffect } from 'react';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { usePortfolios } from './usePortfolios';
import { useSettings } from './useSettings';
import { PortfolioRead } from '@/lib/api/index';

export const useActivePortfolio = () => {
  const activePortfolioId = usePortfolioStore((state) => state.activePortfolioId);
  const hydrated = usePortfolioStore((state) => state.hydrated);
  const setActivePortfolioId = usePortfolioStore((state) => state.setActivePortfolioId);
  const clearActivePortfolioId = usePortfolioStore((state) => state.clearActivePortfolioId);

  const { portfolios, isLoading: isPortfoliosLoading, isError } = usePortfolios();
  const { data: settings, isLoading: isSettingsLoading } = useSettings();

  useEffect(() => {
    if (!hydrated || isPortfoliosLoading || isSettingsLoading) return;

    if (portfolios.length === 0) {
      if (activePortfolioId !== null) {
        clearActivePortfolioId();
      }
      return;
    }

    const currentPortfolioExists = portfolios.some((p: PortfolioRead) => p.id === activePortfolioId);

    if (!currentPortfolioExists) {
      let nextId = portfolios[0].id;
      
      // The settings type might not have default_portfolio_id typed in some versions, so we use any casting safely or check property
      const defaultPortfolioId = (settings as any)?.default_portfolio_id;
      
      if (defaultPortfolioId) {
        const defaultExists = portfolios.some((p: PortfolioRead) => p.id === defaultPortfolioId);
        if (defaultExists) {
          nextId = defaultPortfolioId;
        }
      }
      
      setActivePortfolioId(nextId);
    }
  }, [hydrated, isPortfoliosLoading, isSettingsLoading, portfolios, activePortfolioId, settings, setActivePortfolioId, clearActivePortfolioId]);

  const activePortfolio: PortfolioRead | null = activePortfolioId 
    ? portfolios.find((p: PortfolioRead) => p.id === activePortfolioId) || null 
    : null;

  const isLoading = !hydrated || isPortfoliosLoading || isSettingsLoading;

  return {
    activePortfolioId,
    activePortfolio,
    portfolios,
    isLoading,
    isError,
    setActivePortfolio: setActivePortfolioId,
  };
};
