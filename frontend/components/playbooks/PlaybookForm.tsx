/**
 * PlaybookForm — create or update a playbook.
 */

"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Playbook, PlaybookCreate } from "@/lib/types";
import { Eye, Edit3 } from "lucide-react";

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
  
  // Winrate is stored as 0-1 on backend, displayed as 0-100% on frontend
  const initialWinrate = playbook?.target_winrate 
    ? (Number(playbook.target_winrate) * 100).toString() 
    : "";
  const [targetWinrate, setTargetWinrate] = useState(initialWinrate);
  
  const [contentMarkdown, setContentMarkdown] = useState(playbook?.content_markdown ?? "");
  const [isPreview, setIsPreview] = useState(false);
  const [nameError, setNameError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("Name is required.");
      return;
    }
    setNameError("");
    const payload: PlaybookCreate & { target_winrate?: number; content_markdown?: string } = { name: trimmed };
    if (description.trim()) {
      payload.description = description.trim();
    }
    
    if (contentMarkdown.trim()) {
      payload.content_markdown = contentMarkdown;
    }
    
    if (targetWinrate.trim()) {
      const parsed = parseFloat(targetWinrate);
      if (!isNaN(parsed) && parsed >= 0 && parsed <= 100) {
        payload.target_winrate = parsed / 100;
      }
    }
    
    onSubmit(payload as PlaybookCreate);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label
          htmlFor="playbook-name"
          className="block text-sm font-medium text-muted-foreground mb-1"
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
          className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
          autoFocus
        />
        {nameError && (
          <p className="mt-1 text-xs text-red-400">{nameError}</p>
        )}
      </div>

      <div>
        <label
          htmlFor="target-winrate"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Target Win Rate (%)
        </label>
        <input
          id="target-winrate"
          type="number"
          min="0"
          max="100"
          step="0.01"
          value={targetWinrate}
          onChange={(e) => setTargetWinrate(e.target.value)}
          placeholder="e.g. 55"
          className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm"
        />
      </div>

      <div>
        <label
          htmlFor="playbook-description"
          className="block text-sm font-medium text-muted-foreground mb-1"
        >
          Short Summary (legacy)
        </label>
        <textarea
          id="playbook-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional — brief summary of the setup…"
          rows={2}
          className="w-full px-3 py-2 rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm resize-none"
        />
      </div>
      
      <div className="flex flex-col space-y-1">
        <div className="flex items-center justify-between">
          <label className="block text-sm font-medium text-muted-foreground">
            Playbook Content (Markdown)
          </label>
          <button
            type="button"
            onClick={() => setIsPreview(!isPreview)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {isPreview ? (
              <>
                <Edit3 className="w-3.5 h-3.5" />
                Edit
              </>
            ) : (
              <>
                <Eye className="w-3.5 h-3.5" />
                Preview
              </>
            )}
          </button>
        </div>
        
        {isPreview ? (
          <div className="w-full px-4 py-3 min-h-[200px] rounded-lg bg-secondary border border-border dark:border-border prose prose-sm dark:prose-invert prose-zinc max-w-none">
            {contentMarkdown ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {contentMarkdown}
              </ReactMarkdown>
            ) : (
              <span className="text-muted-foreground italic">Nothing to preview.</span>
            )}
          </div>
        ) : (
          <textarea
            id="playbook-content"
            value={contentMarkdown}
            onChange={(e) => setContentMarkdown(e.target.value)}
            placeholder="Write your detailed strategy rules here using Markdown..."
            rows={10}
            className="w-full px-3 py-2 font-mono rounded-lg bg-secondary border border-border dark:border-border text-foreground placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-sm resize-y"
          />
        )}
      </div>

      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? "Saving…" : playbook ? "Update" : "Create"}
        </button>
      </div>
    </form>
  );
}
