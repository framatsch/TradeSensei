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

/**
 * Tests for QuickNoteInput component.
 *
 * useAddNote (from @/hooks/useNotes) is mocked to avoid real API calls.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuickNoteInput } from "@/components/notes/QuickNoteInput";

// Mock the entire useNotes module
const mockMutate = jest.fn();
let mockIsPending = false;
jest.mock("@/hooks/useNotes", () => ({
  useAddNote: () => ({
    mutate: mockMutate,
    isPending: mockIsPending,
  }),
}));

describe("QuickNoteInput", () => {
  const mockOnClose = jest.fn();
  const tradeId = "trade-123";

  beforeEach(() => {
    mockMutate.mockReset();
    mockIsPending = false;
    mockOnClose.mockClear();
  });

  it("renders the textarea and Save/Cancel buttons", () => {
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    expect(
      screen.getByPlaceholderText(/Live observation/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("Save button is disabled when textarea is empty", () => {
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("Save button is disabled when textarea contains only whitespace", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    await user.type(screen.getByPlaceholderText(/Live observation/i), "   ");
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("Save button is enabled when textarea has non-empty content", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    await user.type(screen.getByPlaceholderText(/Live observation/i), "A note");
    expect(screen.getByRole("button", { name: "Save" })).not.toBeDisabled();
  });

  it("calls addNote mutation with tradeId and trimmed content when Save is clicked", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    await user.type(
      screen.getByPlaceholderText(/Live observation/i),
      "  My quick note  "
    );
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(mockMutate).toHaveBeenCalledWith(
      { tradeId, payload: { content: "My quick note" } },
      expect.any(Object)
    );
  });

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("calls onClose when Escape key is pressed in the textarea", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    const textarea = screen.getByPlaceholderText(/Live observation/i);
    await user.click(textarea);
    await user.keyboard("{Escape}");
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("calls addNote when Ctrl+Enter is pressed", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    const textarea = screen.getByPlaceholderText(/Live observation/i);
    await user.type(textarea, "Ctrl+Enter note");
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(mockMutate).toHaveBeenCalledWith(
      { tradeId, payload: { content: "Ctrl+Enter note" } },
      expect.any(Object)
    );
  });

  it("does NOT call addNote when Ctrl+Enter is pressed with empty content", async () => {
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    const textarea = screen.getByPlaceholderText(/Live observation/i);
    await user.click(textarea);
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("calls onClose after successful save (via onSuccess callback)", async () => {
    mockMutate.mockImplementation((_args: unknown, options: { onSuccess: () => void }) => {
      options.onSuccess();
    });
    const user = userEvent.setup();
    render(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);
    await user.type(screen.getByPlaceholderText(/Live observation/i), "A note");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it("shows 'Saving…' and disables saving non-empty content while pending", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />
    );
    await user.type(screen.getByPlaceholderText(/Live observation/i), "Pending note");
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();

    mockIsPending = true;
    rerender(<QuickNoteInput tradeId={tradeId} onClose={mockOnClose} />);

    const saveButton = screen.getByRole("button", { name: "Saving…" });
    expect(saveButton).toBeDisabled();
    await user.click(saveButton);
    expect(mockMutate).not.toHaveBeenCalled();
  });
});
