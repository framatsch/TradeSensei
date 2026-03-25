/**
 * Tests for NoteForm component.
 *
 * MarkdownRenderer is mocked to avoid pulling in the ESM react-markdown dependency.
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NoteForm } from "@/components/notes/NoteForm";

// Mock MarkdownRenderer to avoid ESM issues from react-markdown
jest.mock("@/components/notes/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-preview">{content}</div>
  ),
}));

const NOTE_MAX_LENGTH = 5_000;
const NOTE_WARN_LENGTH = 4_500;

describe("NoteForm", () => {
  const mockSubmit = jest.fn();

  beforeEach(() => {
    mockSubmit.mockClear();
  });

  it("renders the form with Edit tab active by default", () => {
    render(<NoteForm onSubmit={mockSubmit} />);
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/What happened in this trade/i)).toBeInTheDocument();
  });

  it("shows the character counter at 0/5000 initially", () => {
    render(<NoteForm onSubmit={mockSubmit} />);
    expect(screen.getByText(`0/${NOTE_MAX_LENGTH}`)).toBeInTheDocument();
  });

  it("updates the character counter as the user types", async () => {
    const user = userEvent.setup();
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    await user.type(textarea, "Hello");
    expect(screen.getByText(`5/${NOTE_MAX_LENGTH}`)).toBeInTheDocument();
  });

  it("counter is neutral colour below the warning threshold", async () => {
    render(<NoteForm onSubmit={mockSubmit} />);
    const counter = screen.getByText(`0/${NOTE_MAX_LENGTH}`);
    expect(counter.className).toContain("text-muted-foreground");
  });

  it("counter turns amber when content length is >= 4500", async () => {
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    // Set value directly for performance
    fireEvent.change(textarea, {
      target: { value: "a".repeat(NOTE_WARN_LENGTH) },
    });
    const counter = screen.getByText(`${NOTE_WARN_LENGTH}/${NOTE_MAX_LENGTH}`);
    expect(counter.className).toContain("text-amber-500");
  });

  it("counter turns red and Save button is disabled when over 5000 chars", () => {
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    fireEvent.change(textarea, {
      target: { value: "a".repeat(NOTE_MAX_LENGTH + 1) },
    });
    const counter = screen.getByText(`${NOTE_MAX_LENGTH + 1}/${NOTE_MAX_LENGTH}`);
    expect(counter.className).toContain("text-red-500");
    expect(screen.getByRole("button", { name: "Add Note" })).toBeDisabled();
  });

  it("Save button is enabled when content is within limit", async () => {
    const user = userEvent.setup();
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    await user.type(textarea, "A short note");
    expect(screen.getByRole("button", { name: "Add Note" })).not.toBeDisabled();
  });

  it("shows error message when submitting empty content", async () => {
    const user = userEvent.setup();
    render(<NoteForm onSubmit={mockSubmit} />);
    await user.click(screen.getByRole("button", { name: "Add Note" }));
    expect(screen.getByText(/Note content is required/i)).toBeInTheDocument();
    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with trimmed content and clears form on success", async () => {
    const user = userEvent.setup();
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    await user.type(textarea, "  My trade note  ");
    await user.click(screen.getByRole("button", { name: "Add Note" }));
    expect(mockSubmit).toHaveBeenCalledWith({ content: "My trade note" });
    // Form should be cleared after submit
    expect(textarea).toHaveValue("");
  });

  it("includes emotion in payload when provided", async () => {
    const user = userEvent.setup();
    render(<NoteForm onSubmit={mockSubmit} />);
    const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
    const emotionInput = screen.getByPlaceholderText(/e.g. Confident/i);
    await user.type(textarea, "Good trade");
    await user.type(emotionInput, "Confident");
    await user.click(screen.getByRole("button", { name: "Add Note" }));
    expect(mockSubmit).toHaveBeenCalledWith({
      content: "Good trade",
      emotion: "Confident",
    });
  });

  describe("Edit / Preview tab toggle", () => {
    it("shows textarea in Edit tab", () => {
      render(<NoteForm onSubmit={mockSubmit} />);
      expect(
        screen.getByPlaceholderText(/What happened in this trade/i)
      ).toBeInTheDocument();
      expect(screen.queryByTestId("markdown-preview")).not.toBeInTheDocument();
    });

    it("shows preview area when Preview tab is clicked", async () => {
      const user = userEvent.setup();
      render(<NoteForm onSubmit={mockSubmit} />);
      const textarea = screen.getByPlaceholderText(/What happened in this trade/i);
      await user.type(textarea, "**bold**");
      await user.click(screen.getByRole("button", { name: "Preview" }));
      expect(screen.queryByPlaceholderText(/What happened in this trade/i)).not.toBeInTheDocument();
      expect(screen.getByTestId("markdown-preview")).toHaveTextContent("**bold**");
    });

    it("shows empty preview message when Preview tab is clicked with empty content", async () => {
      const user = userEvent.setup();
      render(<NoteForm onSubmit={mockSubmit} />);
      await user.click(screen.getByRole("button", { name: "Preview" }));
      expect(screen.getByText(/Nothing to preview yet/i)).toBeInTheDocument();
    });

    it("returns to Edit tab when Edit is clicked from Preview", async () => {
      const user = userEvent.setup();
      render(<NoteForm onSubmit={mockSubmit} />);
      await user.click(screen.getByRole("button", { name: "Preview" }));
      await user.click(screen.getByRole("button", { name: "Edit" }));
      expect(
        screen.getByPlaceholderText(/What happened in this trade/i)
      ).toBeInTheDocument();
    });
  });

  it("shows isSubmitting state on the button when isSubmitting=true", () => {
    render(<NoteForm onSubmit={mockSubmit} isSubmitting />);
    expect(screen.getByRole("button", { name: /Adding…/i })).toBeDisabled();
  });
});
