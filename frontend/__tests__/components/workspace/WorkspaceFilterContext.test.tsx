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

jest.mock('@/hooks/useSettings', () => ({
  useSettings: () => ({ data: undefined, isLoading: false, error: null }),
  SETTINGS_KEY: ['settings'],
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
    
    // Allow initial sync to flush
    act(() => {
      jest.advanceTimersByTime(500);
    });
    mockRouterReplace.mockClear();

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
    expect(mockRouterReplace).toHaveBeenCalledWith('/dashboard/workspace/reporting?date_from=2024-02-01&status=closed', { scroll: false });
  });
});
