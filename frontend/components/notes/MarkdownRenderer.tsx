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
        "prose-p:my-1 prose-p:text-slate-200 prose-p:leading-relaxed",
        "prose-headings:text-slate-100 prose-headings:font-semibold",
        "prose-strong:text-slate-100",
        "prose-em:text-slate-300",
        "prose-code:text-amber-300 prose-code:bg-slate-700/60 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs",
        "prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-pre:rounded-lg",
        "prose-blockquote:border-l-slate-500 prose-blockquote:text-slate-400",
        "prose-ul:text-slate-200 prose-ol:text-slate-200",
        "prose-li:my-0.5",
        "prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline",
        "prose-hr:border-slate-700",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
