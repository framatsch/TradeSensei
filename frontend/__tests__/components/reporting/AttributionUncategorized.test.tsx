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
