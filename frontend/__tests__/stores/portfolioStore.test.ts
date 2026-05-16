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

import { usePortfolioStore } from '../../stores/portfolioStore';

describe('portfolioStore', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    localStorage.clear();
    usePortfolioStore.setState({ activePortfolioId: null, hydrated: false });
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('hydrates from localStorage when ID is present', () => {
    localStorage.setItem('active_portfolio_id', 'portfolio-123');
    usePortfolioStore.getState().hydrate();
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('portfolio-123');
    expect(usePortfolioStore.getState().hydrated).toBe(true);
  });

  it('hydrates with null when localStorage is empty', () => {
    usePortfolioStore.getState().hydrate();
    
    expect(usePortfolioStore.getState().activePortfolioId).toBeNull();
    expect(usePortfolioStore.getState().hydrated).toBe(true);
  });

  it('setActivePortfolioId updates state and persists', () => {
    usePortfolioStore.getState().setActivePortfolioId('port-456');
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('port-456');
    expect(localStorage.getItem('active_portfolio_id')).toBe('port-456');
  });

  it('clearActivePortfolioId clears state and localStorage', () => {
    localStorage.setItem('active_portfolio_id', 'port-789');
    usePortfolioStore.setState({ activePortfolioId: 'port-789' });
    
    usePortfolioStore.getState().clearActivePortfolioId();
    
    expect(usePortfolioStore.getState().activePortfolioId).toBeNull();
    expect(localStorage.getItem('active_portfolio_id')).toBeNull();
  });

  it('handles localStorage unavailable gracefully during setActivePortfolioId', () => {
    const setItemSpy = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('localStorage is full');
    });

    usePortfolioStore.getState().setActivePortfolioId('port-999');
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('port-999');
    expect(consoleErrorSpy).toHaveBeenCalled();
    
    setItemSpy.mockRestore();
  });
});
