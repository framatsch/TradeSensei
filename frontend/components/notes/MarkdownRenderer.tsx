/**
 * MarkdownRenderer — renders a markdown string with GitHub-Flavored Markdown
 * support via react-markdown + remark-gfm.
 *
 * Applies Tailwind Typography `prose prose-invert prose-sm` classes for
 * consistent dark-theme styling inside note cards.
 */

"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Props {
  /** Raw markdown string to render. */
  content: string;
  /** Additional CSS class names applied to the wrapper div. */
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: Props) {
  return (
    <div
      className={[
        "prose prose-invert prose-sm max-w-none",
        // Override some prose defaults to fit the dark card style
        "prose-p:my-1 prose-p:text-foreground prose-p:leading-relaxed",
        "prose-headings:text-foreground prose-headings:font-semibold",
        "prose-strong:text-foreground",
        "prose-em:text-muted-foreground",
        "prose-code:text-amber-300 prose-code:bg-secondary/60 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs",
        "prose-pre:bg-background prose-pre:border prose-pre:border-border prose-pre:rounded-lg",
        "prose-blockquote:border-l-slate-500 prose-blockquote:text-muted-foreground",
        "prose-ul:text-foreground prose-ol:text-foreground",
        "prose-li:my-0.5",
        "prose-a:text-primary prose-a:no-underline hover:prose-a:underline",
        "prose-hr:border-border",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
