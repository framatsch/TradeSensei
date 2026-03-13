/**
 * PlaybookForm — create or update a playbook.
 */

"use client";

import { useState } from "react";
import type { Playbook, PlaybookCreate } from "@/lib/types";

interface Props {
  /** If provided, the form is in edit mode and pre-fills the fields. */
  playbook?: Playbook;
  onSubmit: (data: PlaybookCreate) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function PlaybookForm({ playbook, onSubmit, onCancel, isSubmitting = false }: Props) {
  const [name, setName] = useState(playbook?.name ?? "");
  const [description, setDescription] = useState(playbook?.description ?? "");
  const [nameError, setNameError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Name is required.");
      return;
    }
    setNameError("");
    const payload: PlaybookCreate = { name: trimmed };
    if (description.trim()) {
      payload.description = description.trim();
    }
    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="playbook-name"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Name <span className="text-red-400">*</span>
        </label>
        <input
          id="playbook-name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (nameError) setNameError("");
          }}
          placeholder="e.g. Breakout Momentum"
          className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          autoFocus
        />
        {nameError && (
          <p className="mt-1 text-xs text-red-400">{nameError}</p>
        )}
      </div>

      <div>
        <label
          htmlFor="playbook-description"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Description
        </label>
        <textarea
          id="playbook-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional — describe this setup or strategy…"
          rows={3}
          className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
        />
      </div>

      <div className="flex items-center justify-end gap-3 pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 text-sm text-slate-400 hover:text-slate-100 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Saving…" : playbook ? "Update" : "Create"}
        </button>
      </div>
    </form>
  );
}
