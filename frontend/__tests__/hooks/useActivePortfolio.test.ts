import { renderHook } from '@testing-library/react';
import { useActivePortfolio } from '../../hooks/useActivePortfolio';
import * as usePortfoliosHook from '../../hooks/usePortfolios';
import * as useSettingsHook from '../../hooks/useSettings';
import { usePortfolioStore } from '../../stores/portfolioStore';

jest.mock('../../hooks/usePortfolios');
jest.mock('../../hooks/useSettings');

describe('useActivePortfolio', () => {
  const mockPortfolios = [
    { id: 'p1', name: 'Portfolio 1' },
    { id: 'p2', name: 'Portfolio 2' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    usePortfolioStore.setState({ activePortfolioId: null, hydrated: true });
    
    (useSettingsHook.useSettings as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
    });
  });

  it('returns loading state when not hydrated', () => {
    usePortfolioStore.setState({ hydrated: false });
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: [],
      isLoading: false,
      isError: false,
    });

    const { result } = renderHook(() => useActivePortfolio());
    expect(result.current.isLoading).toBe(true);
  });

  it('returns loading state when portfolios are loading', () => {
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: [],
      isLoading: true,
      isError: false,
    });

    const { result } = renderHook(() => useActivePortfolio());
    expect(result.current.isLoading).toBe(true);
  });

  it('clears active portfolio if portfolio list is empty', () => {
    usePortfolioStore.setState({ activePortfolioId: 'p1', hydrated: true });
    
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: [],
      isLoading: false,
      isError: false,
    });

    renderHook(() => useActivePortfolio());
    
    expect(usePortfolioStore.getState().activePortfolioId).toBeNull();
  });

  it('falls back to first portfolio if active ID is stale', () => {
    usePortfolioStore.setState({ activePortfolioId: 'stale-id', hydrated: true });
    
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    renderHook(() => useActivePortfolio());
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('p1');
  });

  it('falls back to default portfolio from settings if active ID is stale and default is present', () => {
    usePortfolioStore.setState({ activePortfolioId: 'stale-id', hydrated: true });
    
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    (useSettingsHook.useSettings as jest.Mock).mockReturnValue({
      data: { default_portfolio_id: 'p2' },
      isLoading: false,
    });

    renderHook(() => useActivePortfolio());
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('p2');
  });

  it('ignores default portfolio from settings if default ID is invalid', () => {
    usePortfolioStore.setState({ activePortfolioId: 'stale-id', hydrated: true });
    
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    (useSettingsHook.useSettings as jest.Mock).mockReturnValue({
      data: { default_portfolio_id: 'non-existent' },
      isLoading: false,
    });

    renderHook(() => useActivePortfolio());
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('p1');
  });

  it('returns current portfolio and no fallback if active ID is valid', () => {
    usePortfolioStore.setState({ activePortfolioId: 'p2', hydrated: true });
    
    (usePortfoliosHook.usePortfolios as jest.Mock).mockReturnValue({
      portfolios: mockPortfolios,
      isLoading: false,
      isError: false,
    });

    const { result } = renderHook(() => useActivePortfolio());
    
    expect(usePortfolioStore.getState().activePortfolioId).toBe('p2');
    expect(result.current.activePortfolio?.id).toBe('p2');
  });
});
