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
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QualitativeMetadataPanel } from "@/components/trades/QualitativeMetadataPanel";
import type { AnnotationDefinitionResponse, Trade } from "@/lib/types";
import { useGetTaxonomies } from "@/hooks/useTaxonomies";
import { useGetAnnotationDefinitions } from "@/hooks/useAnnotationDefinitions";
import {
  useAssignTradeTaxonomy,
  useRemoveTradeTaxonomy,
  useAssignTradeAnnotation,
  useUpdateTradeAnnotation,
} from "@/hooks/useTradeMetadata";
import { useUpdateTrade } from "@/hooks/useTrade";
import { useDeleteNote } from "@/hooks/useNotes";
import { usePlaybooks } from "@/hooks/usePlaybooks";

jest.mock("@/hooks/useFeatureFlag", () => ({
  __esModule: true,
  default: jest.fn(() => false),
}));
jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: jest.fn(),
}));
jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: jest.fn(),
}));
jest.mock("@/hooks/useTradeMetadata", () => ({
  useAssignTradeTaxonomy: jest.fn(),
  useRemoveTradeTaxonomy: jest.fn(),
  useAssignTradeAnnotation: jest.fn(),
  useUpdateTradeAnnotation: jest.fn(),
}));
jest.mock("@/hooks/useTrade", () => ({
  useUpdateTrade: jest.fn(),
}));
jest.mock("@/hooks/useNotes", () => ({
  useDeleteNote: jest.fn(),
}));
jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: jest.fn(),
}));
// Mock MarkdownRenderer to avoid ESM issues from react-markdown (see NoteForm.test.tsx)
jest.mock("@/components/notes/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-preview">{content}</div>
  ),
}));

const convictionDef: AnnotationDefinitionResponse = {
  id: "def-1",
  name: "Conviction",
  type: "int",
  scope: "trades",
  scale_labels: { min: 1, max: 5 },
  is_archived: false,
  created_at: "2024-01-01",
  updated_at: "2024-01-01",
  description: null,
  icon_identifier: null,
};

function buildTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    id: "trade-1",
    position_id: null,
    symbol: "AAPL",
    direction: "LONG",
    asset_class: "EQUITY",
    is_combo: false,
    multiplier: 1,
    quantity: "10",
    entry_price: "100",
    exit_price: null,
    stop_loss: null,
    take_profit: null,
    opened_at: "2024-01-01T00:00:00Z",
    closed_at: null,
    pnl: null,
    net_pnl: null,
    commission: "0",
    journal: null,
    user_rating: null,
    currency: "USD",
    pnl_eur: null,
    net_pnl_eur: null,
    tradingview_link: null,
    image_urls: [],
    playbook_id: null,
    playbook_name: null,
    account_id: "account-1",
    account_name: "Main",
    account_type: "ibkr",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    is_manually_edited: false,
    tags: [],
    taxonomies: [],
    trade_notes: [],
    annotations: [
      {
        annotation_definition_id: "def-1",
        name: "Conviction",
        type: "int",
        scope: "trades",
        icon_identifier: null,
        value: 4,
      },
    ],
    ...overrides,
  };
}

function getMobileSaveBar() {
  return screen.getAllByText("Unsaved changes")
    .map((label) => label.closest(".fixed")).find(Boolean) as HTMLElement;
}

describe("QualitativeMetadataPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useGetTaxonomies as jest.Mock).mockReturnValue({ data: [] });
    (useGetAnnotationDefinitions as jest.Mock).mockReturnValue({ data: [convictionDef] });
    (usePlaybooks as jest.Mock).mockReturnValue({ data: [] });
    (useUpdateTrade as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useDeleteNote as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useAssignTradeTaxonomy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useRemoveTradeTaxonomy as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useAssignTradeAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
    (useUpdateTradeAnnotation as jest.Mock).mockReturnValue({ mutateAsync: jest.fn() });
  });

  it("pre-fills annotation inputs from trade.annotations on initial render", () => {
    render(<QualitativeMetadataPanel trade={buildTrade()} />);

    // Regression test: previously draftAnnotations was always initialized to {}
    // regardless of trade.annotations, so persisted values (including ones written
    // out-of-band via the MCP server) never appeared in the form after a page load.
    expect(screen.getByDisplayValue("4")).toBeInTheDocument();
  });

  it("does not show an 'Unsaved changes' indicator for values already persisted on the trade", () => {
    render(<QualitativeMetadataPanel trade={buildTrade()} />);

    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
  });

  it("re-seeds annotation inputs when switching to a different trade", () => {
    const { rerender } = render(<QualitativeMetadataPanel trade={buildTrade()} />);
    expect(screen.getByDisplayValue("4")).toBeInTheDocument();

    const otherTrade = buildTrade({
      id: "trade-2",
      annotations: [
        {
          annotation_definition_id: "def-1",
          name: "Conviction",
          type: "int",
          scope: "trades",
          icon_identifier: null,
          value: 2,
        },
      ],
    });
    rerender(<QualitativeMetadataPanel trade={otherTrade} />);

    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
  });

  it("filters out inactive playbooks for unassigned trades", () => {
    (usePlaybooks as jest.Mock).mockReturnValue({
      data: [
        { id: "pb-1", name: "Active Strategy", is_active: true },
        { id: "pb-2", name: "Retired Strategy", is_active: false },
      ],
    });

    render(<QualitativeMetadataPanel trade={buildTrade({ playbook_id: null })} />);

    expect(screen.getByRole("option", { name: "Active Strategy" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /retired strategy/i })).not.toBeInTheDocument();
  });

  it("preserves and labels assigned inactive playbook", () => {
    (usePlaybooks as jest.Mock).mockReturnValue({
      data: [
        { id: "pb-1", name: "Active Strategy", is_active: true },
        { id: "pb-2", name: "Retired Strategy", is_active: false },
      ],
    });

    render(<QualitativeMetadataPanel trade={buildTrade({ playbook_id: "pb-2" })} />);

    expect(screen.getByRole("option", { name: "Active Strategy" })).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Retired Strategy (Inactive)" })
    ).toBeInTheDocument();
  });

  it.each(["journal", "playbook", "taxonomy", "annotation"] as const)(
    "reports dirty %s changes and offers scoped desktop and mobile controls",
    async (field) => {
      const user = userEvent.setup();
      const onDirtyChange = jest.fn();
      (usePlaybooks as jest.Mock).mockReturnValue({ data: [{ id: "pb-1", name: "Breakout", is_active: true }] });
      (useGetTaxonomies as jest.Mock).mockReturnValue({ data: [{ id: "tax-1", name: "Patient", is_archived: false }] });
      render(<QualitativeMetadataPanel trade={buildTrade()} onDirtyChange={onDirtyChange} />);
      expect(onDirtyChange).toHaveBeenLastCalledWith(false);

      if (field === "journal") {
        await user.click(screen.getByRole("button", { name: "Edit journal" }));
        await user.type(screen.getByRole("textbox"), "Waited for confirmation.");
      } else if (field === "playbook") {
        await user.selectOptions(screen.getByRole("combobox"), "pb-1");
      } else if (field === "taxonomy") {
        await user.click(screen.getByRole("button", { name: "Patient" }));
      } else {
        await user.clear(screen.getByRole("spinbutton"));
        await user.type(screen.getByRole("spinbutton"), "5");
      }

      expect(onDirtyChange).toHaveBeenLastCalledWith(true);
      const header = screen.getByRole("heading", { name: "Qualitative Analysis & Metadata" }).parentElement!;
      const desktopControls = within(header).getByText("Unsaved changes").parentElement!;
      expect(desktopControls).toHaveClass("hidden", "lg:flex");
      expect(within(desktopControls).getByRole("button", { name: "Save" })).toBeEnabled();
      const mobileBar = getMobileSaveBar();
      expect(mobileBar).toHaveClass("fixed", "bottom-0", "lg:hidden", "pb-[env(safe-area-inset-bottom)]");
      expect(within(mobileBar).getByRole("button", { name: "Save" })).toBeEnabled();

      await user.click(within(mobileBar).getByRole("button", { name: "Cancel" }));

      expect(onDirtyChange).toHaveBeenLastCalledWith(false);
      expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
      expect(screen.getByRole("combobox")).toHaveValue("");
      expect(screen.getByRole("spinbutton")).toHaveValue(4);
      if (field === "journal") expect(screen.getByRole("textbox")).toHaveValue("");
    },
  );

  it("saves from the mobile bar, disables both control variants while saving, and clears dirty state after refresh", async () => {
    const user = userEvent.setup();
    const onDirtyChange = jest.fn();
    let resolveSave!: () => void;
    const pending = new Promise<void>((resolve) => { resolveSave = resolve; });
    const mutateAsync = jest.fn(() => pending);
    (useUpdateTrade as jest.Mock).mockReturnValue({ mutateAsync });
    const trade = buildTrade();
    const { rerender } = render(<QualitativeMetadataPanel trade={trade} onDirtyChange={onDirtyChange} />);
    await user.click(screen.getByRole("button", { name: "Edit journal" }));
    await user.type(screen.getByRole("textbox"), "Saved reflection.");
    const mobileBar = getMobileSaveBar();
    await user.click(within(mobileBar).getByRole("button", { name: "Save" }));

    expect(mutateAsync).toHaveBeenCalledWith({ journal: "Saved reflection.", playbook_id: null });
    const header = screen.getByRole("heading", { name: "Qualitative Analysis & Metadata" }).parentElement!;
    expect(within(header).getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(within(mobileBar).getByRole("button", { name: "Saving..." })).toBeDisabled();
    expect(within(mobileBar).getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("textbox")).toBeDisabled();
    await act(async () => { resolveSave(); });
    // The successful mutation refreshes the persisted trade in the query cache.
    rerender(<QualitativeMetadataPanel trade={{ ...trade, journal: "Saved reflection." }} onDirtyChange={onDirtyChange} />);

    await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(false));
    expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox")).toHaveValue("Saved reflection.");
  });

  it("clears the dirty notification when a dirty panel unmounts", async () => {
    const user = userEvent.setup();
    const onDirtyChange = jest.fn();
    const { unmount } = render(<QualitativeMetadataPanel trade={buildTrade()} onDirtyChange={onDirtyChange} />);
    await user.click(screen.getByRole("button", { name: "Edit journal" }));
    await user.type(screen.getByRole("textbox"), "Draft");
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);

    unmount();

    expect(onDirtyChange).toHaveBeenLastCalledWith(false);
  });
});
