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
  const [emotion, setEmotion] = useState("");
  const { mutate: addNote, isPending } = useAddNote();

  const handleSave = () => {
    const trimmed = content.trim();
    if (!trimmed) return;
    
    const payload: { content: string; emotion?: string } = { content: trimmed };
    if (emotion.trim()) {
      payload.emotion = emotion.trim();
    }
    
    addNote(
      { tradeId, payload },
      {
        onSuccess: () => {
          setContent("");
          setEmotion("");
          onClose();
        },
      }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
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
    <div className="mt-1 p-3 bg-zinc-50/80 dark:bg-zinc-900/80 border border-border dark:border-border rounded-lg">
      <textarea
        autoFocus
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Live observation (e.g. 'Entering scaling out 50%')… (Ctrl+Enter to save)"
        rows={2}
        className="w-full px-2 py-1.5 rounded bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-primary text-xs resize-none"
      />
      <div className="mt-2 flex justify-between items-center gap-2">
        <input
          type="text"
          value={emotion}
          onChange={(e) => setEmotion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Emotion (optional)"
          className="w-40 px-2 py-1 text-xs rounded bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!content.trim() || isPending}
            className="px-3 py-1 text-xs font-medium bg-primary hover:bg-primary/90 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
