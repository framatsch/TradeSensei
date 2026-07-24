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
 * NoteForm — textarea for content + optional emotion input.
 * Includes a character counter and Edit / Preview tab toggle.
 */

"use client";

import { useState, useEffect } from "react";
import type { TradeNoteCreate } from "@/lib/types";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { useSettings } from "@/hooks/useSettings";

const NOTE_MAX_LENGTH = 5_000;
const NOTE_WARN_LENGTH = 4_500;

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

type Tab = "edit" | "preview";

export function NoteForm({ onSubmit, isSubmitting = false }: Props) {
  const [content, setContent] = useState("");
  const [emotion, setEmotion] = useState("");
  const [contentError, setContentError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("edit");
  const { data: settings } = useSettings();

  useEffect(() => {
    // @ts-ignore
    if (settings?.default_markdown_mode === "preview" && content.trim().length > 0) {
      setActiveTab("preview");
    }
    // @ts-ignore
  }, [settings?.default_markdown_mode]);

  const charCount = content.length;
  const isOverLimit = charCount > NOTE_MAX_LENGTH;
  const isNearLimit = charCount >= NOTE_WARN_LENGTH && !isOverLimit;

  const counterClass = isOverLimit
    ? "text-red-500"
    : isNearLimit
      ? "text-amber-500"
      : "text-muted-foreground";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) {
      setContentError("Note content is required.");
      return;
    }
    if (isOverLimit) {
      setContentError(`Note must be ${NOTE_MAX_LENGTH} characters or fewer.`);
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
    setActiveTab("edit");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Tab bar */}
      <div className="flex gap-1 border-b border-border">
        <button
          type="button"
          onClick={() => setActiveTab("edit")}
          className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
            activeTab === "edit"
              ? "bg-secondary text-foreground border border-b-0 border-border dark:border-border"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("preview")}
          className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
            activeTab === "preview"
              ? "bg-secondary text-foreground border border-b-0 border-border dark:border-border"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Preview
        </button>
      </div>

      <div>
        {activeTab === "edit" ? (
          <>
            <textarea
              id="note-content"
              value={content}
              onChange={(e) => {
                setContent(e.target.value);
                if (contentError) setContentError("");
              }}
              placeholder="Record a point-in-time observation during the trade (e.g., 'Moved stop to breakeven', 'Price hesitating at VWAP')..."
              rows={4}
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm resize-none"
            />
            {/* Character counter */}
            <div className="mt-1 flex items-center justify-between">
              <div>
                {contentError && (
                  <p className="text-xs text-red-400">{contentError}</p>
                )}
              </div>
              <span className={`text-xs ${counterClass}`}>
                {charCount}/{NOTE_MAX_LENGTH}
              </span>
            </div>
          </>
        ) : (
          <div className="min-h-[96px] px-3 py-2 rounded-lg bg-secondary/50 border border-border dark:border-border">
            {content.trim() ? (
              <MarkdownRenderer content={content} />
            ) : (
              <p className="text-sm text-muted-foreground italic">Nothing to preview yet.</p>
            )}
          </div>
        )}
      </div>

      <div className="flex items-end gap-3">
        <div className="flex-1">
          <label
            htmlFor="note-emotion"
            className="block text-xs font-medium text-muted-foreground mb-1"
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
              className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
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
          disabled={isSubmitting || isOverLimit}
          className="px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {isSubmitting ? "Adding…" : "Add Note"}
        </button>
      </div>
    </form>
  );
}
