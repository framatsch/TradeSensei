/**
 * NoteForm — textarea for content + optional emotion input.
 */

"use client";

import { useState } from "react";
import type { TradeNoteCreate } from "@/lib/types";

const EMOTION_OPTIONS = [
  "Confident",
  "Anxious",
  "Fearful",
  "Greedy",
  "Disciplined",
  "Frustrated",
  "Calm",
  "Excited",
  "Regretful",
];

interface Props {
  onSubmit: (data: TradeNoteCreate) => void;
  isSubmitting?: boolean;
}

export function NoteForm({ onSubmit, isSubmitting = false }: Props) {
  const [content, setContent] = useState("");
  const [emotion, setEmotion] = useState("");
  const [contentError, setContentError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) {
      setContentError("Note content is required.");
      return;
    }
    setContentError("");
    const payload: TradeNoteCreate = { content: trimmed };
    if (emotion.trim()) {
      payload.emotion = emotion.trim();
    }
    onSubmit(payload);
    setContent("");
    setEmotion("");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label
          htmlFor="note-content"
          className="block text-xs font-medium text-slate-400 mb-1"
        >
          Note <span className="text-red-400">*</span>
        </label>
        <textarea
          id="note-content"
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            if (contentError) setContentError("");
          }}
          placeholder="What happened in this trade? Execution, mistakes, observations…"
          rows={3}
          className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
        />
        {contentError && (
          <p className="mt-1 text-xs text-red-400">{contentError}</p>
        )}
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label
            htmlFor="note-emotion"
            className="block text-xs font-medium text-slate-400 mb-1"
          >
            Emotion (optional)
          </label>
          <div className="relative">
            <input
              id="note-emotion"
              type="text"
              list="emotion-options"
              value={emotion}
              onChange={(e) => setEmotion(e.target.value)}
              placeholder="e.g. Confident, Fearful…"
              className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
            <datalist id="emotion-options">
              {EMOTION_OPTIONS.map((opt) => (
                <option key={opt} value={opt} />
              ))}
            </datalist>
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {isSubmitting ? "Adding…" : "Add Note"}
        </button>
      </div>
    </form>
  );
}
