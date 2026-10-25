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
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CheckinForm } from "@/components/checkin/CheckinForm";

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => ({
    get: () => null,
  }),
}));

jest.mock("react-markdown", () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock("remark-gfm", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("rehype-sanitize", () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock("@/hooks/useCheckinDefinitions", () => ({
  useMarketIndexes: () => ({
    data: [{ id: "idx-1", symbol: "SPY", name: "S&P 500", is_active: true, tradingview_url: "https://tradingview.com/spy" }],
  }),
}));

jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: () => ({
    data: [
      {
        id: "def-1",
        name: "Market Regime",
        type: "string_enum",
        scope: "checkins",
        is_archived: false,
        scale_labels: { options: ["Trending", "Range"] },
      },
    ],
  }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({
    data: [{ id: "tag-1", name: "Bullish", color_hex: "#22c55e", is_archived: false }],
  }),
}));

jest.mock("@/hooks/useCheckinMetadata", () => ({
  useAssignCheckinTaxonomy: () => ({ mutateAsync: jest.fn() }),
  useRemoveCheckinTaxonomy: () => ({ mutateAsync: jest.fn() }),
  useAssignCheckinAnnotation: () => ({ mutateAsync: jest.fn() }),
  useUpdateCheckinAnnotation: () => ({ mutateAsync: jest.fn() }),
  useRemoveCheckinAnnotation: () => ({ mutateAsync: jest.fn() }),
}));

describe("CheckinForm", () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockReplace.mockReset();
  });

  it("buffers tags on new check-in and passes them to onSave for Save and Save & Close", async () => {
    const user = userEvent.setup();
    const mockOnSave = jest.fn().mockResolvedValue(undefined);

    render(
      <CheckinForm
        date="2026-10-25"
        entry={null}
        prevEntryDate="2026-10-23"
        nextEntryDate={null}
        onSave={mockOnSave}
        onDelete={jest.fn()}
        isSaving={false}
        isDeleting={false}
      />
    );

    // Select a tag while creating a new check-in
    await user.click(screen.getByRole("button", { name: "Bullish" }));

    // Enter market notes
    const notesTextarea = screen.getByLabelText("Market notes (Markdown)");
    await user.type(notesTextarea, "Strong pre-market bid");

    // Click "Save" (stays in edit mode)
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({
        date: "2026-10-25",
        notes: "Strong pre-market bid",
      }),
      expect.objectContaining({
        bufferedTagIds: ["tag-1"],
        closeAfterSave: false,
      })
    );
    expect(screen.getByLabelText("Market notes (Markdown)")).toBeInTheDocument();

    // Click "Save & Close" (exits edit mode)
    await user.click(screen.getByRole("button", { name: "Save & Close" }));
    expect(mockOnSave).toHaveBeenLastCalledWith(
      expect.any(Object),
      expect.objectContaining({ closeAfterSave: true })
    );
    expect(mockReplace).toHaveBeenCalledWith("/dashboard/checkins/2026-10-25");
  });

  it("navigates to previous existing entry when Previous Entry button is clicked", async () => {
    const user = userEvent.setup();

    render(
      <CheckinForm
        date="2026-10-25"
        entry={null}
        prevEntryDate="2026-10-22"
        nextEntryDate={null}
        onSave={jest.fn()}
        onDelete={jest.fn()}
        isSaving={false}
        isDeleting={false}
      />
    );

    const prevBtn = screen.getByRole("button", { name: "Previous Entry" });
    const nextBtn = screen.getByRole("button", { name: "Next Entry" });

    expect(prevBtn).not.toBeDisabled();
    expect(nextBtn).toBeDisabled();

    await user.click(prevBtn);
    expect(mockPush).toHaveBeenCalledWith("/dashboard/checkins/2026-10-22");
  });
});
