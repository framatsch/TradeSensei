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
 * NoteList — vertical list of trade notes with add, edit, and delete.
 */

"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useNotes, useAddNote, useUpdateNote, useDeleteNote } from "@/hooks/useNotes";
import { NoteForm } from "./NoteForm";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { Spinner } from "@/components/ui/Spinner";
import type { TradeNoteCreate } from "@/lib/types";
import { formatDistanceToNow } from "date-fns";

interface Props {
  tradeId: string;
}

const EMOTION_COLORS: Record<string, string> = {
  confident: "badge-positive",
  disciplined: "badge-positive",
  calm: "badge-positive",
  anxious: "badge-caution",
  fearful: "badge-negative",
  greedy: "badge-negative",
  excited: "badge-caution",
  frustrated: "badge-negative",
  regretful: "badge-negative",
};

function getEmotionClass(emotion: string): string {
  return (
    EMOTION_COLORS[emotion.toLowerCase()] ??
    "badge-neutral"
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  const relative = formatDistanceToNow(date, { addSuffix: true });
  const absolute = date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  return `${relative} · ${absolute}`;
}

const EMOTIONS = [
  "confident", "disciplined", "calm", "anxious",
  "fearful", "greedy", "excited", "frustrated", "regretful",
];

export function NoteList({ tradeId }: Props) {
  const { data: notes, isLoading, isError, error } = useNotes(tradeId);
  const { mutate: addNote, isPending: adding } = useAddNote();
  const { mutate: updateNote } = useUpdateNote();
  const { mutate: deleteNote } = useDeleteNote();

  const [collapsed, setCollapsed] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editEmotion, setEditEmotion] = useState<string>("");

  const noteCount = notes?.length ?? 0;

  const handleAdd = (payload: TradeNoteCreate) => {
    addNote({ tradeId, payload });
  };

  const handleDelete = (noteId: string) => {
    deleteNote({ tradeId, noteId });
  };

  const startEdit = (noteId: string, content: string, emotion: string | null) => {
    setEditingId(noteId);
    setEditContent(content);
    setEditEmotion(emotion ?? "");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditContent("");
    setEditEmotion("");
  };

  const saveEdit = (noteId: string) => {
    updateNote(
      {
        tradeId,
        noteId,
        payload: {
          content: editContent,
          emotion: editEmotion || null,
        },
      },
      { onSuccess: cancelEdit }
    );
  };

  return (
    <div className="solid-card shadow-sm w-full">
      <div className={`flex items-center justify-between p-5 ${collapsed ? "" : "border-b border-border"}`}>
        <h2 className="text-base font-semibold text-foreground">
          <button
            type="button"
            aria-expanded={!collapsed}
            onClick={() => setCollapsed((c) => !c)}
            className="flex items-center gap-2 text-left hover:text-primary transition-colors"
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 shrink-0 text-muted-foreground" />
            )}
            <span>Quick Notes</span>
            {noteCount > 0 && (
              <span className="font-mono text-xs font-normal text-muted-foreground">({noteCount})</span>
            )}
          </button>
        </h2>
      </div>

      <div className={collapsed ? "hidden" : "p-5 space-y-4"}>
        {/* Notes list */}
        {isLoading ? (
          <div className="flex justify-center py-10">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="py-8 text-center">
            <p className="text-danger text-sm">{error.message}</p>
          </div>
        ) : notes && notes.length > 0 ? (
          <div className="space-y-3">
            {notes.map((note) =>
              editingId === note.id ? (
                /* ── Inline edit mode ── */
                <div
                  key={note.id}
                  className="panel-sub border-primary/50 p-4 space-y-3"
                >
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={4}
                    className="w-full rounded-lg border border-border bg-secondary text-sm text-foreground px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  />
                  <select
                    value={editEmotion}
                    onChange={(e) => setEditEmotion(e.target.value)}
                    className="rounded-lg border border-border bg-secondary text-sm text-foreground px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">No emotion</option>
                    {EMOTIONS.map((e) => (
                      <option key={e} value={e}>
                        {e.charAt(0).toUpperCase() + e.slice(1)}
                      </option>
                    ))}
                  </select>
                  <div className="flex gap-2">
                    <button
                      onClick={() => saveEdit(note.id)}
                      disabled={!editContent.trim()}
                      className="px-3 py-1.5 text-xs font-medium bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-md transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-3 py-1.5 text-xs font-medium text-muted-foreground bg-secondary hover:text-foreground hover:bg-muted rounded-md transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                /* ── Read mode ── */
                <div
                  key={note.id}
                  className="group relative panel-sub p-4"
                >
                  {/* Action buttons */}
                  <div className="absolute top-3 right-3 flex gap-1 opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100 transition-opacity">
                    <button
                      onClick={() => startEdit(note.id, note.content, note.emotion)}
                      className="p-1 rounded-md text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
                      title="Edit note"
                      aria-label="Edit note"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDelete(note.id)}
                      className="p-1 rounded-md text-muted-foreground hover:text-danger hover:bg-danger/10 transition-colors"
                      title="Delete note"
                      aria-label="Delete note"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                        <path d="M10 11v6M14 11v6" />
                        <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                      </svg>
                    </button>
                  </div>

                  {/* Content */}
                  <div className="pr-16">
                    <MarkdownRenderer content={note.content} />
                  </div>

                  {/* Footer */}
                  <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                    {note.emotion && (
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getEmotionClass(note.emotion)}`}
                      >
                        {note.emotion}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(note.created_at)}
                    </span>
                  </div>
                </div>
              )
            )}
          </div>
        ) : (
          <div className="py-6 text-center text-muted-foreground">
            <p className="text-sm">No notes yet. Add your first note below.</p>
          </div>
        )}

        {/* Add note form */}
        <div className="border-t border-border pt-4">
          <NoteForm onSubmit={handleAdd} isSubmitting={adding} />
        </div>
      </div>
    </div>
  );
}
