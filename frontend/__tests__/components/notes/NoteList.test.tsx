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
import { NoteList } from "@/components/notes/NoteList";
import { useNotes, useAddNote, useUpdateNote, useDeleteNote } from "@/hooks/useNotes";

jest.mock("@/hooks/useNotes", () => ({
  useNotes: jest.fn(),
  useAddNote: jest.fn(),
  useUpdateNote: jest.fn(),
  useDeleteNote: jest.fn(),
}));

jest.mock("@/hooks/useSettings", () => ({
  useSettings: () => ({ data: undefined, isLoading: false, error: null }),
}));

jest.mock("@/components/notes/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-preview">{content}</div>
  ),
}));

describe("NoteList", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useNotes as jest.Mock).mockReturnValue({
      data: [
        {
          id: "note-1",
          trade_id: "trade-1",
          content: "First quick note",
          emotion: "calm",
          created_at: "2026-10-24T10:00:00Z",
          updated_at: "2026-10-24T10:00:00Z",
        },
      ],
      isLoading: false,
      isError: false,
      error: null,
    });
    (useAddNote as jest.Mock).mockReturnValue({ mutate: jest.fn(), isPending: false });
    (useUpdateNote as jest.Mock).mockReturnValue({ mutate: jest.fn() });
    (useDeleteNote as jest.Mock).mockReturnValue({ mutate: jest.fn() });
  });

  it("starts expanded by default and collapses/expands while keeping the form mounted", async () => {
    const user = userEvent.setup();
    render(<NoteList tradeId="trade-1" />);

    const toggle = screen.getByRole("button", { name: /Quick Notes \(1\)/i });
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Unsaved note text");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(textarea.closest(".hidden")).not.toBeNull();

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(textarea.closest(".hidden")).toBeNull();
    expect(textarea).toHaveValue("Unsaved note text");
  });
});
