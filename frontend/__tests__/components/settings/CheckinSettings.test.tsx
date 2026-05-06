import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CheckinSettings } from "@/components/settings/CheckinSettings";
import {
  useMarketPhases,
  useCreateMarketPhase,
  useUpdateMarketPhase,
  useCheckinFields,
  useCreateCheckinField,
  useUpdateCheckinField,
  useMarketIndexes,
  useCreateMarketIndex,
  useUpdateMarketIndex,
  useDeleteMarketIndex,
} from "@/hooks/useCheckinDefinitions";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@testing-library/jest-dom";

jest.mock("@/hooks/useCheckinDefinitions");

const mockUseMarketPhases = useMarketPhases as jest.Mock;
const mockUseCreateMarketPhase = useCreateMarketPhase as jest.Mock;
const mockUseUpdateMarketPhase = useUpdateMarketPhase as jest.Mock;
const mockUseCheckinFields = useCheckinFields as jest.Mock;
const mockUseCreateCheckinField = useCreateCheckinField as jest.Mock;
const mockUseUpdateCheckinField = useUpdateCheckinField as jest.Mock;
const mockUseMarketIndexes = useMarketIndexes as jest.Mock;
const mockUseCreateMarketIndex = useCreateMarketIndex as jest.Mock;
const mockUseUpdateMarketIndex = useUpdateMarketIndex as jest.Mock;
const mockUseDeleteMarketIndex = useDeleteMarketIndex as jest.Mock;

const mockPhases = [
  {
    id: "phase-1",
    user_id: "user-1",
    name: "bullish",
    label: "Bullish",
    color_hex: "#22c55e",
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "phase-2",
    user_id: "user-1",
    name: "bearish",
    label: "Bearish",
    color_hex: "#ef4444",
    is_active: true,
    created_at: "2024-01-02T00:00:00Z",
  },
  {
    id: "phase-3",
    user_id: "user-1",
    name: "sideways",
    label: "Sideways",
    color_hex: "#f59e0b",
    is_active: false,
    created_at: "2024-01-03T00:00:00Z",
  },
];

const mockFields = [
  {
    id: "field-1",
    user_id: "user-1",
    field_name: "mood-level",
    field_type: "integer" as const,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "field-2",
    user_id: "user-1",
    field_name: "rule-followed",
    field_type: "boolean" as const,
    is_active: true,
    created_at: "2024-01-02T00:00:00Z",
  },
];

describe("CheckinSettings", () => {
  let queryClient: QueryClient;
  let mockPhaseMutate: jest.Mock;
  let mockPhaseCreate: jest.Mock;
  let mockFieldMutate: jest.Mock;
  let mockFieldCreate: jest.Mock;

  beforeEach(() => {
    queryClient = new QueryClient();

    mockPhaseMutate = jest.fn();
    mockPhaseCreate = jest.fn();
    mockFieldMutate = jest.fn();
    mockFieldCreate = jest.fn();

    mockUseMarketIndexes.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });
    mockUseCreateMarketIndex.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
    });
    mockUseUpdateMarketIndex.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
    });
    mockUseDeleteMarketIndex.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
    });

    mockUseMarketPhases.mockReturnValue({
      data: mockPhases,
      isLoading: false,
      isError: false,
    });
    mockUseCreateMarketPhase.mockReturnValue({
      mutate: mockPhaseCreate,
      isPending: false,
    });
    mockUseUpdateMarketPhase.mockReturnValue({
      mutate: mockPhaseMutate,
      isPending: false,
    });
    mockUseCheckinFields.mockReturnValue({
      data: mockFields,
      isLoading: false,
      isError: false,
    });
    mockUseCreateCheckinField.mockReturnValue({
      mutate: mockFieldCreate,
      isPending: false,
    });
    mockUseUpdateCheckinField.mockReturnValue({
      mutate: mockFieldMutate,
      isPending: false,
    });

    jest.clearAllMocks();
  });

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <CheckinSettings />
      </QueryClientProvider>
    );
  }

  // ─── 4.2 Rendering tests ────────────────────────────────────────────────────

  describe("rendering", () => {
    it("renders the Market Phases section header and table", () => {
      renderComponent();
      expect(screen.getByText("MARKET PHASES")).toBeInTheDocument();
      expect(screen.getByText("Bullish")).toBeInTheDocument();
      expect(screen.getByText("Bearish")).toBeInTheDocument();
      expect(screen.getByText("Sideways")).toBeInTheDocument();
    });

    it("renders the Custom Metrics section header and table", () => {
      renderComponent();
      expect(screen.getByText("CUSTOM METRICS")).toBeInTheDocument();
      expect(screen.getByText("mood-level")).toBeInTheDocument();
      expect(screen.getByText("rule-followed")).toBeInTheDocument();
    });

    it("renders '+ New Phase' button", () => {
      renderComponent();
      expect(screen.getByText("+ New Phase")).toBeInTheDocument();
    });

    it("renders '+ New Metric' button", () => {
      renderComponent();
      expect(screen.getByText("+ New Metric")).toBeInTheDocument();
    });

    it("renders Key column as immutable text for market phases", () => {
      renderComponent();
      expect(screen.getByText("bullish")).toBeInTheDocument();
      expect(screen.getByText("bearish")).toBeInTheDocument();
    });

    it("renders Typ column as Badge for custom metrics", () => {
      renderComponent();
      expect(screen.getByText("Integer")).toBeInTheDocument();
      expect(screen.getByText("Boolean")).toBeInTheDocument();
    });

    it("shows Active/Inactive status labels", () => {
      renderComponent();
      const activeLabels = screen.getAllByText("Active");
      const inactiveLabels = screen.getAllByText("Inactive");
      expect(activeLabels.length).toBeGreaterThanOrEqual(2);
      expect(inactiveLabels.length).toBeGreaterThanOrEqual(1);
    });

    it("renders Status toggles as switches", () => {
      renderComponent();
      const switches = screen.getAllByRole("switch");
      // mockPhases: 3 phases (2 active, 1 inactive) + mockFields: 2 fields (2 active)
      expect(switches.length).toBe(5);
    });
  });

  // ─── 4.3 Immutable field behavior ───────────────────────────────────────────

  describe("immutable fields", () => {
    it("displays market phase Key as plain text, not an input", () => {
      renderComponent();
      const textElement = screen.getByText("bullish");
      expect(textElement.tagName).not.toBe("INPUT");
    });

    it("does not render inputs for market phase Key column", () => {
      renderComponent();
      // All inputs should be edit-related or modal inputs, never for Key
      const inputs = screen.queryAllByRole("textbox");
      // No Key fields are inputs before edit is triggered
      const keyInputs = inputs.filter((el) => (el as HTMLInputElement).value === "bullish");
      expect(keyInputs.length).toBe(0);
    });

    it("displays checkin field Key as plain text, not an input", () => {
      renderComponent();
      const textElement = screen.getByText("mood-level");
      expect(textElement.tagName).not.toBe("INPUT");
    });

    it("displays checkin field Typ as a Badge, not a select or input", () => {
      renderComponent();
      const integerBadge = screen.getByText("Integer");
      expect(integerBadge.tagName).toBe("SPAN");
      const booleanBadge = screen.getByText("Boolean");
      expect(booleanBadge.tagName).toBe("SPAN");
    });
  });

  // ─── 4.4 Warning modal on deactivation ──────────────────────────────────────

  describe("warning modal", () => {
    it("does not show warning when activating an inactive market phase", async () => {
      renderComponent();

      // "sideways" is inactive — find its toggle (all toggles)
      const switches = screen.getAllByRole("switch");
      const sidewaysSwitch = switches[2]; // 3rd phase (index 0,1,2)
      expect(sidewaysSwitch).toHaveAttribute("aria-checked", "false");

      fireEvent.click(sidewaysSwitch);

      await waitFor(() => {
        // Direct mutation, no modal for market phases
        expect(mockPhaseMutate).toHaveBeenCalledWith({
          id: "phase-3",
          payload: { is_active: true },
        });
      });
    });

    it("shows warning modal when deactivating a custom metric", async () => {
      renderComponent();

      // "mood-level" is first custom metric — 5th switch overall
      const switches = screen.getAllByRole("switch");
      const moodSwitch = switches[3]; // 4th switch (index 3) = first checkin field
      expect(moodSwitch).toHaveAttribute("aria-checked", "true");

      fireEvent.click(moodSwitch);

      await waitFor(() => {
        expect(screen.getByText('Deactivate "mood-level"?')).toBeInTheDocument();
      });
    });

    it("shows the correct warning text in the modal", async () => {
      renderComponent();

      const switches = screen.getAllByRole("switch");
      const moodSwitch = switches[3];
      fireEvent.click(moodSwitch);

      await waitFor(() => {
        expect(
          screen.getByText(/Historical data for this metric will remain visible/)
        ).toBeInTheDocument();
      });
    });

    it("calls PATCH when confirming deactivation in the modal", async () => {
      renderComponent();

      const switches = screen.getAllByRole("switch");
      const moodSwitch = switches[3];
      fireEvent.click(moodSwitch);

      await waitFor(() => {
        expect(screen.getByText("Deactivate")).toBeInTheDocument();
      });

      const deactivateButton = screen.getByRole("button", { name: "Deactivate" });
      fireEvent.click(deactivateButton);

      await waitFor(() => {
        expect(mockFieldMutate).toHaveBeenCalledWith(
          {
            id: "field-1",
            payload: { is_active: false },
          },
          expect.objectContaining({ onSuccess: expect.any(Function) })
        );
      });
    });

    it("cancels deactivation when Cancel is clicked in the modal", async () => {
      renderComponent();

      const switches = screen.getAllByRole("switch");
      const moodSwitch = switches[3];
      fireEvent.click(moodSwitch);

      await waitFor(() => {
        expect(screen.getByText("Cancel")).toBeInTheDocument();
      });

      const cancelButton = screen.getByText("Cancel");
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText('Deactivate "mood-level"?')).not.toBeInTheDocument();
      });
      expect(mockFieldMutate).not.toHaveBeenCalled();
    });
  });
});