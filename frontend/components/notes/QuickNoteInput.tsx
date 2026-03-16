/**
 * QuickNoteInput — collapsible inline note form for use inside trade rows.
 * Renders a textarea with Save/Cancel buttons. Save is disabled when empty.
 */

"use client";

import { useState } from "react";
import { useAddNote } from "@/hooks/useNotes";

interface Props {
  tradeId: string;
  /** Called when the user cancels or successfully saves. */
  onClose: () => void;
}

export function QuickNoteInput({ tradeId, onClose }: Props) {
  const [content, setContent] = useState("");
  const { mutate: addNote, isPending } = useAddNote();

  const handleSave = () => {
    const trimmed = content.trim();
    if (!trimmed) return;
    addNote(
      { tradeId, payload: { content: trimmed } },
      {
        onSuccess: () => {
          setContent("");
          onClose();
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl/Cmd + Enter to save
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
    // Escape to cancel
    if (e.key === "Escape") {
      onClose();
    }
  };

  return (
    <div className="mt-1 p-3 bg-slate-800/80 border border-slate-600 rounded-lg">
      <textarea
        autoFocus
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Quick note… (Ctrl+Enter to save, Esc to cancel)"
        rows={2}
        className="w-full px-2 py-1.5 rounded bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs resize-none"
      />
      <div className="mt-2 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={!content.trim() || isPending}
          className="px-3 py-1 text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
