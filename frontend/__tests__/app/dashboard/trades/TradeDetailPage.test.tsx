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
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TradeDetailPage from "@/app/dashboard/trades/[id]/page";
import { useTrade } from "@/hooks/useTrade";
import { useTradeExecutions } from "@/hooks/useExecutions";
import { useTradeNavigation } from "@/hooks/useTradeNavigation";
import useFeatureFlag from "@/hooks/useFeatureFlag";
import type { LogicalExecution, Trade } from "@/lib/types";

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "trade-1" }),
}));

jest.mock("@/hooks/useTrade", () => ({
  useTrade: jest.fn(),
  useUpdateTrade: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("@/hooks/useExecutions", () => ({
  useTradeExecutions: jest.fn(),
}));

// Navigation's QueryClient/session-storage behavior is tested in its own suite.
jest.mock("@/hooks/useTradeNavigation", () => ({
  useTradeNavigation: jest.fn(),
}));

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", activePortfolio: { id: "portfolio-1" } }),
}));

jest.mock("@/hooks/useFeatureFlag", () => jest.fn(() => false));
jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({ data: [] }),
}));
jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: () => ({ data: [] }),
}));
jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: () => ({ data: [] }),
}));
jest.mock("@/hooks/useTradeMetadata", () => ({
  useAssignTradeTaxonomy: () => ({ mutateAsync: jest.fn() }),
  useRemoveTradeTaxonomy: () => ({ mutateAsync: jest.fn() }),
  useAssignTradeAnnotation: () => ({ mutateAsync: jest.fn() }),
  useUpdateTradeAnnotation: () => ({ mutateAsync: jest.fn() }),
}));
jest.mock("@/hooks/useNotes", () => ({
  useDeleteNote: () => ({ mutateAsync: jest.fn() }),
}));
jest.mock("@/hooks/useScreenshots", () => ({
  useUploadScreenshot: () => ({ mutate: jest.fn(), isPending: false }),
  useDeleteScreenshot: () => ({ mutate: jest.fn(), isPending: false }),
}));
jest.mock("@/components/notes/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => <div>{content}</div>,
}));
jest.mock("@/components/charts/TradeChart", () => ({
  TradeChart: () => <div role="img" aria-label="Trade price chart" />,
}));
jest.mock("@/components/trades/ExecutionSummaryCard", () => ({
  ExecutionSummaryCard: () => <h2>Execution Summary</h2>,
}));
jest.mock("@/components/trades/ExecutionLegsTable", () => ({
  ExecutionLegsTable: () => <h2>Execution Legs</h2>,
}));
jest.mock("@/components/notes/NoteList", () => ({
  NoteList: () => <h2>Quick Notes</h2>,
}));
// Deliberately omit dialog roles from modal doubles: page-state keyboard guards
// must work independently of the global dialog/menu role guard.
jest.mock("@/components/trades/CorrectTradeModal", () => ({
  CorrectTradeModal: ({ onClose }: { onClose: () => void }) => (
    <button onClick={onClose}>Close correction</button>
  ),
}));
jest.mock("@/components/trades/TradePickerModal", () => ({
  TradePickerModal: ({ onClose, onConfirm }: { onClose: () => void; onConfirm: (trades: Trade[]) => void }) => (
    <div>
      <button onClick={onClose}>Close picker</button>
      <button onClick={() => onConfirm([{ id: "trade-2" } as Trade])}>Continue merge</button>
    </div>
  ),
}));
jest.mock("@/components/trades/MergePreviewModal", () => ({
  MergePreviewModal: ({ onClose }: { onClose: () => void }) => (
    <button onClick={onClose}>Close merge preview</button>
  ),
}));

const baseTrade: Trade = {
  id: "trade-1",
  symbol: "AAPL",
  direction: "LONG",
  asset_class: "EQUITY",
  is_combo: false,
  multiplier: 1,
  quantity: "10",
  chart_quantity: "10",
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
  position_id: null,
  user_rating: 0,
  trade_notes: [],
  has_conflict: false,
  has_unlinked_executions: false,
  corporate_action_impact: [],
};

const navigation = {
  available: true,
  prevId: "trade-0",
  nextId: "trade-2",
  canGoPrev: true,
  canGoNext: true,
  prevSymbol: "MSFT",
  nextSymbol: "TSLA",
  position: 2,
  total: 128,
  sourceLabel: "Filtered trade list",
  isLoadingNext: false,
  navigationError: null,
  goPrev: jest.fn(),
  goNext: jest.fn().mockResolvedValue(undefined),
  backHref: "/dashboard/trades?result=losers&sort_by=pnl&sort_dir=asc",
};

function setTrade(overrides: Partial<Trade> = {}) {
  (useTrade as jest.Mock).mockReturnValue({
    data: { ...baseTrade, ...overrides },
    isLoading: false,
    isError: false,
  });
}

function getPane(name: "Overview" | "Journal" | "Executions") {
  return screen.getByRole("tabpanel", { name: new RegExp(`^${name}`) });
}

function getDesktopHeader() {
  return screen.getByText("Final P&L").closest(".solid-card") as HTMLElement;
}

beforeEach(() => {
  jest.clearAllMocks();
  setTrade();
  (useTradeExecutions as jest.Mock).mockReturnValue({ data: [], isLoading: false });
  (useTradeNavigation as jest.Mock).mockReturnValue({ ...navigation });
  (useFeatureFlag as jest.Mock).mockReturnValue(false);
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("TradeDetailPage responsive sections", () => {
  it("renders the corporate action indicator when corporate_action_impact is present", () => {
    setTrade({
      corporate_action_impact: [{
        id: "ca-1", symbol: "AAPL", date: "2024-02-01", ratio: "0.25", old_conid: null, new_conid: null,
      }],
    });

    render(<TradeDetailPage />);

    expect(within(screen.getByRole("banner")).getByLabelText(/Affected by a corporate action/i)).toBeInTheDocument();
    expect(within(getDesktopHeader()).getByLabelText(/Affected by a corporate action/i)).toBeInTheDocument();
  });

  it("does not render the corporate action indicator when corporate_action_impact is empty", () => {
    render(<TradeDetailPage />);

    expect(within(screen.getByRole("banner")).queryByLabelText(/Affected by a corporate action/i)).not.toBeInTheDocument();
    expect(within(getDesktopHeader()).queryByLabelText(/Affected by a corporate action/i)).not.toBeInTheDocument();
  });

  it("renders unlinked execution notice when has_unlinked_executions is true", () => {
    setTrade({ has_unlinked_executions: true });

    render(<TradeDetailPage />);

    expect(screen.getByText(/protected trade has unlinked executions from import/i)).toBeInTheDocument();
  });

  it("hides unlinked execution notice when has_unlinked_executions is false", () => {
    render(<TradeDetailPage />);

    expect(screen.queryByText(/protected trade has unlinked executions from import/i)).not.toBeInTheDocument();
  });

  it("selects Overview by default while keeping every pane mounted for desktop", () => {
    render(<TradeDetailPage />);

    const tabs = within(screen.getByRole("tablist", { name: "Trade view sections" }));
    expect(tabs.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(tabs.getByRole("tab", { name: "Journal" })).toHaveAttribute("aria-selected", "false");
    expect(tabs.getByRole("tab", { name: "Executions (0)" })).toHaveAttribute("aria-selected", "false");
    expect(within(getPane("Overview")).getByRole("img", { name: "Trade price chart" })).toBeInTheDocument();
    expect(within(getPane("Overview")).getByRole("heading", { name: "Performance" })).toBeInTheDocument();
    expect(within(getPane("Overview")).getByRole("heading", { name: "Execution Summary" })).toBeInTheDocument();
    expect(within(getPane("Journal")).getByRole("heading", { name: "Qualitative Analysis & Metadata" })).toBeInTheDocument();
    expect(within(getPane("Executions")).getByRole("heading", { name: "Execution Legs" })).toBeInTheDocument();
    // jsdom does not apply Tailwind breakpoints; verify the CSS visibility contract.
    expect(getPane("Overview")).not.toHaveClass("hidden");
    expect(getPane("Journal")).toHaveClass("hidden", "lg:block");
    expect(getPane("Executions")).toHaveClass("hidden", "lg:block");
  });

  it("switches all three tabs without remounting the price chart", async () => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    const chart = within(getPane("Overview")).getByRole("img", { name: "Trade price chart" });

    for (const name of ["Journal", "Executions", "Overview"] as const) {
      await user.click(screen.getByRole("tab", { name: new RegExp(`^${name}`) }));

      expect(screen.getByRole("tab", { name: new RegExp(`^${name}`) })).toHaveAttribute("aria-selected", "true");
      expect(getPane(name)).not.toHaveClass("hidden");
      for (const other of ["Overview", "Journal", "Executions"] as const) {
        if (other !== name) expect(getPane(other)).toHaveClass("hidden", "lg:block");
      }
      expect(within(getPane("Overview")).getByRole("img", { name: "Trade price chart" })).toBe(chart);
    }
  });

  it("preserves the journal draft and dirty navigation state across tab switches", async () => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    expect(useTradeNavigation).toHaveBeenLastCalledWith("trade-1", { isDirty: false });
    await user.click(screen.getByRole("tab", { name: "Journal" }));
    await user.click(within(getPane("Journal")).getByRole("button", { name: "Edit journal" }));
    const textarea = within(getPane("Journal")).getByRole("textbox");
    await user.type(textarea, "Waited for the retest.");

    expect(within(screen.getByRole("tab", { name: /^Journal/ })).getByRole("img", { name: "Unsaved journal changes" })).toBeInTheDocument();
    expect(useTradeNavigation).toHaveBeenLastCalledWith("trade-1", { isDirty: true });
    await user.click(screen.getByRole("tab", { name: "Overview" }));
    await user.click(screen.getByRole("tab", { name: /^Journal/ }));

    expect(within(getPane("Journal")).getByRole("textbox")).toBe(textarea);
    expect(textarea).toHaveValue("Waited for the retest.");
    expect(screen.getByRole("img", { name: "Unsaved journal changes" })).toBeInTheDocument();
    expect(useTradeNavigation).toHaveBeenLastCalledWith("trade-1", { isDirty: true });

    const mobileSaveBar = within(getPane("Journal")).getAllByText("Unsaved changes")
      .map((label) => label.closest(".fixed")).find(Boolean) as HTMLElement;
    await user.click(within(mobileSaveBar).getByRole("button", { name: "Cancel" }));
    expect(textarea).toHaveValue("");
    expect(screen.queryByRole("img", { name: "Unsaved journal changes" })).not.toBeInTheDocument();
    expect(useTradeNavigation).toHaveBeenLastCalledWith("trade-1", { isDirty: false });
  });

  it("counts active executions without counting deleted legs", () => {
    (useTradeExecutions as jest.Mock).mockReturnValue({
      data: [false, false, false, false, true].map((deleted, index) => ({ id: `exec-${index}`, deleted } as LogicalExecution)),
    });
    render(<TradeDetailPage />);

    expect(screen.getByRole("tab", { name: "Executions (4)" })).toBeInTheDocument();
    expect(useTradeExecutions).toHaveBeenCalledWith("trade-1", "portfolio-1");
  });

  it("switches to Executions before scrolling when the conflict banner is reviewed", async () => {
    const user = userEvent.setup();
    setTrade({ has_conflict: true });
    render(<TradeDetailPage />);
    const scrollTarget = document.getElementById("executions-table")!;
    const scrollIntoView = jest.fn(() => {
      expect(screen.getByRole("tab", { name: "Executions (0)" })).toHaveAttribute("aria-selected", "true");
      expect(getPane("Executions")).not.toHaveClass("hidden");
    });
    scrollTarget.scrollIntoView = scrollIntoView;

    await user.click(screen.getByRole("button", { name: "Review executions" }));

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth" }));
  });

  it("renders quick notes in the Journal pane only when enabled", () => {
    (useFeatureFlag as jest.Mock).mockReturnValue(true);
    render(<TradeDetailPage />);

    expect(within(getPane("Journal")).getByRole("heading", { name: "Quick Notes" })).toBeInTheDocument();
    expect(within(getPane("Overview")).queryByRole("heading", { name: "Quick Notes" })).not.toBeInTheDocument();
  });

  it("restores the list URL through both back links", () => {
    render(<TradeDetailPage />);

    expect(within(screen.getByRole("banner")).getByRole("link", { name: "Back to Trades" })).toHaveAttribute("href", navigation.backHref);
    const desktopNav = screen.getByText("Back to Trades").parentElement!;
    expect(within(desktopNav).getByRole("link", { name: "Back to Trades" })).toHaveAttribute("href", navigation.backHref);
  });
});

describe("TradeDetailPage keyboard navigation", () => {
  function pressArrows(target: HTMLElement = document.body, options: KeyboardEventInit = {}) {
    fireEvent(target, new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true, cancelable: true, ...options }));
    fireEvent(target, new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true, cancelable: true, ...options }));
  }

  function expectNoNavigation() {
    expect(navigation.goPrev).not.toHaveBeenCalled();
    expect(navigation.goNext).not.toHaveBeenCalled();
  }

  async function openDesktopAction(user: ReturnType<typeof userEvent.setup>, label: string) {
    await user.click(within(getDesktopHeader()).getByRole("button", { name: "Trade actions" }));
    await user.click(screen.getByRole("button", { name: label }));
  }

  it.each([
    ["ArrowLeft", "goPrev", "goNext"],
    ["ArrowRight", "goNext", "goPrev"],
  ] as const)("navigates once with %s and prevents the default arrow action", (key, callback, other) => {
    render(<TradeDetailPage />);
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    fireEvent(document.body, event);

    expect(navigation[callback]).toHaveBeenCalledTimes(1);
    expect(navigation[other]).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(true);
  });

  it("ignores unrelated keys", () => {
    render(<TradeDetailPage />);
    fireEvent.keyDown(document.body, { key: "Enter" });
    fireEvent.keyDown(document.body, { key: "ArrowUp" });

    expectNoNavigation();
  });

  it.each(["input", "textarea", "select"] as const)("ignores both arrows in a focused %s", async (target) => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    let input: HTMLElement;
    if (target === "input") {
      await user.click(within(getPane("Overview")).getByTitle("Click to edit Stop Loss"));
      input = screen.getByRole("spinbutton", { name: "Stop Loss" });
    } else {
      await user.click(screen.getByRole("tab", { name: "Journal" }));
      if (target === "textarea") {
        await user.click(within(getPane("Journal")).getByRole("button", { name: "Edit journal" }));
        input = within(getPane("Journal")).getByRole("textbox");
      } else {
        input = within(getPane("Journal")).getByRole("combobox");
      }
    }
    await user.click(input);
    expect(input).toHaveFocus();
    await user.keyboard("{ArrowLeft}{ArrowRight}");

    expectNoNavigation();
  });

  it("ignores arrows from descendants of a contenteditable element", () => {
    render(<>
      <TradeDetailPage />
      <div contentEditable suppressContentEditableWarning><span>Rich journal draft</span></div>
    </>);
    pressArrows(screen.getByText("Rich journal draft"));

    expectNoNavigation();
  });

  it("does not treat contenteditable=false as an editor", () => {
    render(<>
      <TradeDetailPage />
      <div contentEditable={false}><span>Read-only journal preview</span></div>
    </>);
    pressArrows(screen.getByText("Read-only journal preview"));

    expect(navigation.goPrev).toHaveBeenCalledTimes(1);
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it.each(["altKey", "ctrlKey", "metaKey", "shiftKey"] as const)("ignores arrows with %s", (modifier) => {
    render(<TradeDetailPage />);
    pressArrows(document.body, { [modifier]: true });

    expectNoNavigation();
  });

  it("ignores arrows already handled by a focused widget", () => {
    render(<>
      <TradeDetailPage />
      <button onKeyDown={(event) => event.preventDefault()}>Widget keyboard handler</button>
    </>);
    pressArrows(screen.getByRole("button", { name: "Widget keyboard handler" }));

    expectNoNavigation();
  });

  it.each([
    ["ArrowLeft", { canGoPrev: false }],
    ["ArrowRight", { canGoNext: false }],
  ] as const)("ignores %s when its navigation direction is disabled", (key, disabled) => {
    (useTradeNavigation as jest.Mock).mockReturnValue({ ...navigation, ...disabled });
    render(<TradeDetailPage />);
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    fireEvent(document.body, event);

    expectNoNavigation();
    expect(event.defaultPrevented).toBe(false);
  });

  it("ignores arrows without list navigation context", () => {
    (useTradeNavigation as jest.Mock).mockReturnValue({ ...navigation, available: false });
    render(<TradeDetailPage />);
    pressArrows();

    expectNoNavigation();
  });

  it("ignores both arrows while the next page is loading", () => {
    (useTradeNavigation as jest.Mock).mockReturnValue({ ...navigation, isLoadingNext: true });
    render(<TradeDetailPage />);
    pressArrows();

    expectNoNavigation();
  });

  it("ignores arrows while the trade itself is loading", () => {
    (useTrade as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, isError: false });
    render(<TradeDetailPage />);
    pressArrows();

    expectNoNavigation();
  });

  it("ignores arrows while the desktop overflow menu is open and resumes after closing it", async () => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    const trigger = within(getDesktopHeader()).getByRole("button", { name: "Trade actions" });
    await user.click(trigger);
    expect(screen.getByRole("button", { name: "Correct Trade…" })).toBeInTheDocument();
    // This hand-rolled desktop menu has no menu role, so its state guard matters.
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    pressArrows();
    expectNoNavigation();

    await user.click(trigger);
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it("ignores arrows while the mobile Radix menu is open and resumes after Escape", async () => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    within(screen.getByRole("banner")).getByRole("button", { name: "Trade actions" }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("menu")).toBeInTheDocument();
    pressArrows();
    expectNoNavigation();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["correction", "Correct Trade…", "Close correction"],
    ["trade picker", "Merge with…", "Close picker"],
    ["merge preview", "Merge with…", "Close merge preview"],
  ])("ignores arrows while the page's %s modal is open", async (modal, action, closeLabel) => {
    const user = userEvent.setup();
    render(<TradeDetailPage />);
    await openDesktopAction(user, action);
    if (modal === "merge preview") await user.click(screen.getByRole("button", { name: "Continue merge" }));
    expect(screen.getByRole("button", { name: closeLabel })).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    pressArrows();
    expectNoNavigation();

    await user.click(screen.getByRole("button", { name: closeLabel }));
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["dialog", { role: "dialog" }],
    ["menu", { role: "menu" }],
    ["aria-modal", { "aria-modal": true }],
  ] as const)("ignores arrows when another component exposes an open %s", (_label, attributes) => {
    const { rerender } = render(<>
      <TradeDetailPage />
      <div {...attributes}>External overlay</div>
    </>);
    pressArrows();
    expectNoNavigation();

    rerender(<><TradeDetailPage /></>);
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it("treats the real screenshot lightbox as a modal dialog and blocks arrows until it closes", async () => {
    const user = userEvent.setup();
    setTrade({ image_urls: ["/storage/screenshots/chart.png"] });
    render(<TradeDetailPage />);
    await user.click(within(getPane("Overview")).getByRole("button", { name: /Screenshots/ }));
    await user.click(within(getPane("Overview")).getByRole("img", { name: "screenshot" }));

    const lightbox = screen.getByRole("dialog", { name: "Screenshot viewer" });
    expect(lightbox).toHaveAttribute("aria-modal", "true");
    expect(within(lightbox).getByRole("img", { name: "Screenshot" })).toHaveAttribute("src", "/api/proxy/storage/screenshots/chart.png");
    pressArrows();
    expectNoNavigation();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Screenshot viewer" })).not.toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it("removes the keyboard listener when the detail page unmounts", () => {
    const { unmount } = render(<TradeDetailPage />);
    unmount();
    pressArrows();

    expectNoNavigation();
  });
});
