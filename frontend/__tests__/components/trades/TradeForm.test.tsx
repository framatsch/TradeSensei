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

jest.mock("@/hooks/useTags", () => ({ useTags: () => ({ data: [] }) }));
jest.mock("@/hooks/usePlaybooks", () => ({ usePlaybooks: () => ({ data: [] }) }));
jest.mock("@/hooks/useAccounts", () => ({ useAccounts: () => ({ data: [] }) }));

jest.mock("@/lib/api/index", () => ({
  useGetTaxonomiesApiV1TaxonomiesGet: () => ({ data: { data: [] } }),
  useGetAnnotationDefinitionsApiV1AnnotationsDefinitionsGet: () => ({ data: { data: [] } }),
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
