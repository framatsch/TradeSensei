/**
 * NoteList — vertical list of trade notes with add-note form at the bottom.
 */

"use client";

import { useNotes, useAddNote, useDeleteNote } from "@/hooks/useNotes";
import { NoteForm } from "./NoteForm";
import { Spinner } from "@/components/ui/Spinner";
import type { TradeNoteCreate } from "@/lib/types";

interface Props {
  tradeId: string;
}

const EMOTION_COLORS: Record<string, string> = {
  confident:
    "bg-emerald-900/50 text-emerald-400 border-emerald-800",
  disciplined:
    "bg-blue-900/50 text-blue-400 border-blue-800",
  calm:
    "bg-sky-900/50 text-sky-400 border-sky-800",
  anxious:
    "bg-yellow-900/50 text-yellow-400 border-yellow-800",
  fearful:
    "bg-orange-900/50 text-orange-400 border-orange-800",
  greedy:
    "bg-purple-900/50 text-purple-400 border-purple-800",
  excited:
    "bg-indigo-900/50 text-indigo-400 border-indigo-800",
  frustrated:
    "bg-red-900/50 text-red-400 border-red-800",
  regretful:
    "bg-pink-900/50 text-pink-400 border-pink-800",
};

function getEmotionClass(emotion: string): string {
  return (
    EMOTION_COLORS[emotion.toLowerCase()] ??
    "bg-slate-700 text-slate-300 border-slate-600"
  );
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function NoteList({ tradeId }: Props) {
  const { data: notes, isLoading, isError, error } = useNotes(tradeId);
  const { mutate: addNote, isPending: adding } = useAddNote();
  const { mutate: deleteNote } = useDeleteNote();

  const handleAdd = (payload: TradeNoteCreate) => {
    addNote({ tradeId, payload });
  };

  const handleDelete = (noteId: string) => {
    deleteNote({ tradeId, noteId });
  };

  return (
    <div className="space-y-4">
      {/* Notes list */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : isError ? (
        <div className="py-8 text-center">
          <p className="text-red-400 text-sm">{error.message}</p>
        </div>
      ) : notes && notes.length > 0 ? (
        <div className="space-y-3">
          {notes.map((note) => (
            <div
              key={note.id}
              className="group relative bg-slate-800/60 border border-slate-700 rounded-xl p-4"
            >
              {/* Delete button */}
              <button
                onClick={() => handleDelete(note.id)}
                className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 p-1 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-900/20 transition-all"
                title="Delete note"
                aria-label="Delete note"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="w-4 h-4"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6M14 11v6" />
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                </svg>
              </button>

              {/* Content */}
              <p className="text-sm text-slate-200 leading-relaxed pr-8 whitespace-pre-wrap">
                {note.content}
              </p>

              {/* Footer */}
              <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                {note.emotion && (
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${getEmotionClass(
                      note.emotion
                    )}`}
                  >
                    {note.emotion}
                  </span>
                )}
                <span className="text-xs text-slate-500">
                  {formatDateTime(note.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-8 text-center text-slate-500">
          <p className="text-sm">No notes yet. Add your first note below.</p>
        </div>
      )}

      {/* Add note form */}
      <div className="border-t border-slate-700 pt-4">
        <NoteForm onSubmit={handleAdd} isSubmitting={adding} />
      </div>
    </div>
  );
}
