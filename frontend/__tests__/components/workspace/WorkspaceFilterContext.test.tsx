import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { WorkspaceFilterProvider, useWorkspaceFilter } from '@/components/workspace/WorkspaceFilterContext';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

// Mock Next.js navigation hooks
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(),
  useSearchParams: jest.fn(),
}));

const TestComponent = () => {
  const { filter, setFilter } = useWorkspaceFilter();

  return (
    <div>
      <div data-testid="date_from">{filter.date_from || 'none'}</div>
      <button onClick={() => setFilter(prev => ({ ...prev, date_from: '2024-02-01' }))}>
        Update Filter
      </button>
    </div>
  );
};

describe('WorkspaceFilterContext', () => {
  let mockRouterPush: jest.Mock;
  let mockRouterReplace: jest.Mock;
  let mockSearchParams: URLSearchParams;

  beforeEach(() => {
    jest.useFakeTimers();
    mockRouterPush = jest.fn();
    mockRouterReplace = jest.fn();
    mockSearchParams = new URLSearchParams();

    (useRouter as jest.Mock).mockReturnValue({ push: mockRouterPush, replace: mockRouterReplace });
    (usePathname as jest.Mock).mockReturnValue('/dashboard/workspace/reporting');
    (useSearchParams as jest.Mock).mockImplementation(() => mockSearchParams);
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test('initial state is read from URL params', () => {
    mockSearchParams.set('date_from', '2024-01-01');
    render(
      <WorkspaceFilterProvider>
        <TestComponent />
      </WorkspaceFilterProvider>
    );

    expect(screen.getByTestId('date_from')).toHaveTextContent('2024-01-01');
  });

  test('setter updates context value immediately but debounces URL update', () => {
    render(
      <WorkspaceFilterProvider>
        <TestComponent />
      </WorkspaceFilterProvider>
    );

    expect(screen.getByTestId('date_from')).toHaveTextContent('none');

    act(() => {
      screen.getByText('Update Filter').click();
    });

    // Context updates immediately
    expect(screen.getByTestId('date_from')).toHaveTextContent('2024-02-01');

    // URL should not be updated before 300ms
    act(() => {
      jest.advanceTimersByTime(200);
    });
    expect(mockRouterReplace).not.toHaveBeenCalled();

    // URL should be updated after debounce
    act(() => {
      jest.advanceTimersByTime(150);
    });
    expect(mockRouterReplace).toHaveBeenCalledWith('/dashboard/workspace/reporting?date_from=2024-02-01', { scroll: false });
  });
});
