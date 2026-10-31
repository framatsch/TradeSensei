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
      
      const defaultPortfolioId = settings?.default_portfolio_id;
      
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
