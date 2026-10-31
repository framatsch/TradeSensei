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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TradeForm } from "@/components/trades/TradeForm";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/hooks/useTrade", () => ({
  useCreateTrade: () => ({ mutate: jest.fn(), isPending: false }),
  useUpdateTrade: () => ({ mutate: jest.fn(), isPending: false }),
  useTradeImageUploadUrl: () => ({ mutateAsync: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/usePlaybooks", () => ({ usePlaybooks: () => ({ data: [] }) }));
jest.mock("@/hooks/useAccounts", () => ({ useAccounts: () => ({ data: [] }) }));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({ data: [] }),
}));

jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: () => ({ data: [] }),
}));

describe("TradeForm", () => {
  it("COMBO checkbox disables Advanced Mode toggle and sets isAdvancedMode to true", async () => {
    render(<TradeForm />);
    
    const comboCheckbox = screen.getByLabelText("COMBO position");
    const advancedModeCheckbox = document.querySelector('input[name="isAdvancedMode"]') as HTMLInputElement;
    
    // Initial state
    expect(advancedModeCheckbox).not.toBeChecked();

    // Check COMBO
    fireEvent.click(comboCheckbox);

    await waitFor(() => {
      expect(advancedModeCheckbox).toBeChecked();
    });
  });

  it("execution legs timestamps auto-derive opened_at/closed_at and disable fields", async () => {
    // Setup date to be deterministic
    const systemTime = new Date('2023-01-01T12:00:00Z');
    jest.useFakeTimers().setSystemTime(systemTime);

    render(<TradeForm />);
    
    const advancedModeCheckbox = document.querySelector('input[name="isAdvancedMode"]') as HTMLInputElement;
    fireEvent.click(advancedModeCheckbox);

    // Add a leg
    const addLegButton = screen.getByText(/Add Leg/i);
    fireEvent.click(addLegButton);

    const openedAtInput = document.querySelector('input[name="opened_at"]') as HTMLInputElement;
    const closedAtInput = document.querySelector('input[name="closed_at"]') as HTMLInputElement;

    // wait for useEffect
    await waitFor(() => {
      expect(openedAtInput.value).toBeTruthy();
    });
    expect(openedAtInput).toBeDisabled();
    expect(closedAtInput).toBeDisabled();

    jest.useRealTimers();
  });

  it("blocks form submit with validation error when zero legs in Advanced Mode", async () => {
    render(<TradeForm />);
    
    // Check advanced mode
    const advancedModeCheckbox = document.querySelector('input[name="isAdvancedMode"]') as HTMLInputElement;
    fireEvent.click(advancedModeCheckbox);

    // Fill minimum fields
    fireEvent.change(screen.getByPlaceholderText("AAPL"), { target: { value: "AAPL" } });

    // Submit
    fireEvent.click(screen.getByText("Create Trade"));

    await waitFor(() => {
      expect(screen.getByText(/At least one execution leg is required in Advanced Mode/)).toBeInTheDocument();
    });
  });
});
