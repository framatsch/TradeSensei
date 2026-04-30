import { create } from 'zustand';

export interface PortfolioState {
  activePortfolioId: string | null;
  hydrated: boolean;
  setActivePortfolioId: (id: string) => void;
  clearActivePortfolioId: () => void;
  hydrate: () => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  activePortfolioId: null,
  hydrated: false,
  setActivePortfolioId: (id: string) => {
    set({ activePortfolioId: id });
    try {
      localStorage.setItem('active_portfolio_id', id);
    } catch (err) {
      console.error('Failed to save active_portfolio_id to localStorage', err);
    }
  },
  clearActivePortfolioId: () => {
    set({ activePortfolioId: null });
    try {
      localStorage.removeItem('active_portfolio_id');
    } catch (err) {
      console.error('Failed to remove active_portfolio_id from localStorage', err);
    }
  },
  hydrate: () => {
    let id: string | null = null;
    try {
      const stored = localStorage.getItem('active_portfolio_id');
      if (stored) {
        id = stored;
      }
    } catch (err) {
      console.error('Failed to read active_portfolio_id from localStorage', err);
    }
    set({ activePortfolioId: id, hydrated: true });
  },
}));
