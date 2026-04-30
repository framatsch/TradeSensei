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
