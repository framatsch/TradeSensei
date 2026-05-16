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
import { render, screen } from '@testing-library/react';
import { UncategorizedBanner } from '@/components/reporting/Widgets';

describe('UncategorizedBanner', () => {
  test('renders nothing when both counts are 0', () => {
    const { container } = render(
      <UncategorizedBanner unmatchedCount={0} phaseUnsetCount={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  test('renders unmatched count when > 0', () => {
    render(<UncategorizedBanner unmatchedCount={7} phaseUnsetCount={0} />);
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText(/trades without check-in/i)).toBeInTheDocument();
  });

  test('renders phase unset count when > 0', () => {
    render(<UncategorizedBanner unmatchedCount={0} phaseUnsetCount={4} />);
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText(/trades with unset market regime/i)).toBeInTheDocument();
  });

  test('renders both counts when both > 0', () => {
    render(<UncategorizedBanner unmatchedCount={3} phaseUnsetCount={2} />);
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText(/trades without check-in/i)).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText(/trades with unset market regime/i)).toBeInTheDocument();
  });
});
